"""
Labirentten Kaçış (Maze Escape)
Gelişmiş engeller, seviye sistemi, tuzaklar, düşmanlar ve güçlendirmeler içeren 2D Python oyunu.
Gereksinim: pygame (pip install pygame)
"""

import sys
import math
import random
import time
import pygame

# ---------------------------------------------------------
# SABİTLER & AYARLAR
# ---------------------------------------------------------
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 680
FPS = 60

# Renk Paleti (Modern Koyu / Neon Tema)
COLOR_BG = (15, 18, 28)
COLOR_WALL = (38, 45, 68)
COLOR_WALL_OUTLINE = (55, 66, 99)
COLOR_FLOOR = (22, 27, 41)
COLOR_PLAYER = (0, 230, 255)
COLOR_PLAYER_GLOW = (0, 150, 200, 60)
COLOR_EXIT = (50, 255, 126)
COLOR_SPIKE_OFF = (60, 60, 75)
COLOR_SPIKE_ON = (255, 65, 84)
COLOR_LASER = (255, 50, 120)
COLOR_ENEMY = (255, 75, 43)
COLOR_KEY = (255, 215, 0)
COLOR_DOOR = (180, 100, 255)
COLOR_COIN = (255, 220, 50)
COLOR_TEXT = (240, 245, 255)
COLOR_HUD_BG = (12, 15, 24, 210)


# ---------------------------------------------------------
# LABİRENT OLUŞTURUCU (Recursive Backtracker)
# ---------------------------------------------------------
class MazeGenerator:
    @staticmethod
    def generate(cols, rows):
        """
        cols ve rows tek sayı olmalıdır.
        1: Duvar, 0: Yol
        """
        grid = [[1 for _ in range(cols)] for _ in range(rows)]

        def get_neighbors(r, c):
            neighbors = []
            directions = [(-2, 0), (2, 0), (0, -2), (0, 2)]
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 1 <= nr < rows - 1 and 1 <= nc < cols - 1:
                    if grid[nr][nc] == 1:
                        neighbors.append((nr, nc, dr, dc))
            return neighbors

        # Başlangıç noktası
        start_r, start_c = 1, 1
        grid[start_r][start_c] = 0
        stack = [(start_r, start_c)]

        while stack:
            curr_r, curr_c = stack[-1]
            neighbors = get_neighbors(curr_r, curr_c)
            if neighbors:
                nr, nc, dr, dc = random.choice(neighbors)
                # Aradaki duvarı ve hedef hücreyi kır
                grid[curr_r + dr // 2][curr_c + dc // 2] = 0
                grid[nr][nc] = 0
                stack.append((nr, nc))
            else:
                stack.pop()

        # Birkaç ekstra bağlantı açarak labirentte alternatif rotalar oluştur (Daha dinamik kaçış)
        extra_openings = (cols * rows) // 40
        for _ in range(extra_openings):
            er = random.randrange(2, rows - 2)
            ec = random.randrange(2, cols - 2)
            if grid[er][ec] == 1:
                # Eğer komşu zıt iki hücre boşsa duvarı kaldır
                if (grid[er - 1][ec] == 0 and grid[er + 1][ec] == 0) or \
                   (grid[er][ec - 1] == 0 and grid[er][ec + 1] == 0):
                    grid[er][ec] = 0

        return grid


# ---------------------------------------------------------
# PARÇACIK EFEKT SİSTEMİ
# ---------------------------------------------------------
class Particle:
    def __init__(self, x, y, color, vx, vy, life, size=3):
        self.x = x
        self.y = y
        self.color = color
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        alpha_ratio = max(0.0, self.life / self.max_life)
        cur_size = max(1, int(self.size * alpha_ratio))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), cur_size)


# ---------------------------------------------------------
# OYUN NESNELERİ (ENGELLER, DÜŞMANLAR, TOPLANABİLİRLER)
# ---------------------------------------------------------
class SpikeTrap:
    """Zamanla açılıp kapanan dikenli zemin tuzağı"""
    def __init__(self, c, r, tile_size, cycle_time=2.4, offset=0.0):
        self.c = c
        self.r = r
        self.tile_size = tile_size
        self.rect = pygame.Rect(c * tile_size, r * tile_size, tile_size, tile_size)
        self.cycle_time = cycle_time
        self.timer = offset % cycle_time
        self.is_active = False

    def update(self, dt):
        self.timer = (self.timer + dt) % self.cycle_time
        # Döngünün yarısında aktif, yarısında inaktif
        self.is_active = self.timer > (self.cycle_time * 0.45)

    def draw(self, surface):
        pad = 4
        sub_rect = self.rect.inflate(-pad * 2, -pad * 2)
        if self.is_active:
            pygame.draw.rect(surface, COLOR_SPIKE_ON, sub_rect, border_radius=4)
            # Diken üçgenleri
            mid_x = self.rect.centerx
            mid_y = self.rect.centery
            pts = [(mid_x, self.rect.top + 6), (self.rect.left + 6, self.rect.bottom - 6), (self.rect.right - 6, self.rect.bottom - 6)]
            pygame.draw.polygon(surface, (255, 230, 230), pts)
        else:
            pygame.draw.rect(surface, COLOR_SPIKE_OFF, sub_rect, width=2, border_radius=4)
            pygame.draw.circle(surface, (80, 85, 100), self.rect.center, 3)


class LaserBarrier:
    """Periyodik olarak açılan ve kapanan ölümcül lazer bariyeri"""
    def __init__(self, c1, r1, c2, r2, tile_size, cycle_time=3.0, offset=0.0):
        self.c1, self.r1 = c1, r1
        self.c2, self.r2 = c2, r2
        self.tile_size = tile_size
        self.x1 = c1 * tile_size + tile_size // 2
        self.y1 = r1 * tile_size + tile_size // 2
        self.x2 = c2 * tile_size + tile_size // 2
        self.y2 = r2 * tile_size + tile_size // 2
        self.cycle_time = cycle_time
        self.timer = offset % cycle_time
        self.is_active = False

    def update(self, dt):
        self.timer = (self.timer + dt) % self.cycle_time
        self.is_active = self.timer > (self.cycle_time * 0.4)

    def check_player_collision(self, px, py, radius):
        if not self.is_active:
            return False
        # Nokta ile doğru parçası arasındaki en kısa mesafe
        lx = self.x2 - self.x1
        ly = self.y2 - self.y1
        line_len_sq = lx * lx + ly * ly
        if line_len_sq == 0:
            return math.hypot(px - self.x1, py - self.y1) < radius

        t = max(0.0, min(1.0, ((px - self.x1) * lx + (py - self.y1) * ly) / line_len_sq))
        proj_x = self.x1 + t * lx
        proj_y = self.y1 + t * ly
        dist = math.hypot(px - proj_x, py - proj_y)
        return dist < (radius + 4)

    def draw(self, surface):
        if self.is_active:
            # Parlayan Lazer Hattı
            pygame.draw.line(surface, (255, 100, 180), (self.x1, self.y1), (self.x2, self.y2), 6)
            pygame.draw.line(surface, (255, 255, 255), (self.x1, self.y1), (self.x2, self.y2), 2)
            pygame.draw.circle(surface, COLOR_LASER, (self.x1, self.y1), 6)
            pygame.draw.circle(surface, COLOR_LASER, (self.x2, self.y2), 6)
        else:
            # Pasif emitörler
            pygame.draw.circle(surface, (80, 80, 100), (self.x1, self.y1), 4)
            pygame.draw.circle(surface, (80, 80, 100), (self.x2, self.y2), 4)
            pygame.draw.line(surface, (40, 45, 60), (self.x1, self.y1), (self.x2, self.y2), 1)


class PatrollingEnemy:
    """Koridorlarda devriye gezen veya oyuncuya doğru yönelen gardiyan"""
    def __init__(self, x, y, tile_size, speed=90):
        self.x = float(x)
        self.y = float(y)
        self.tile_size = tile_size
        self.speed = speed
        self.radius = tile_size * 0.35
        self.current_dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.target_c = int(self.x // tile_size)
        self.target_r = int(self.y // tile_size)
        self.anim_phase = random.uniform(0, 6.28)

    def update(self, dt, maze_grid, rows, cols, player_pos):
        self.anim_phase += dt * 5

        # Mevcut kare koordinatı
        cur_c = int(self.x // self.tile_size)
        cur_r = int(self.y // self.tile_size)

        # Hedefe yaklaşıldıysa yeni yön belirle
        target_x = self.target_c * self.tile_size + self.tile_size // 2
        target_y = self.target_r * self.tile_size + self.tile_size // 2

        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)

        step = self.speed * dt
        if dist <= step:
            self.x = target_x
            self.y = target_y
            cur_c = self.target_c
            cur_r = self.target_r

            # Gidilebilecek komşu hücreler
            valid_dirs = []
            for d in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nc = cur_c + d[0]
                nr = cur_r + d[1]
                if 0 <= nc < cols and 0 <= nr < rows and maze_grid[nr][nc] == 0:
                    valid_dirs.append(d)

            if valid_dirs:
                # Oyuncuya yakınsa oyuncuya doğru gitmeye öncelik ver
                px, py = player_pos
                p_c = int(px // self.tile_size)
                p_r = int(py // self.tile_size)

                # %40 olasılıkla oyuncu yönünü takip et, yoksa rastgele koridor seç
                if random.random() < 0.4 and (abs(p_c - cur_c) + abs(p_r - cur_r) <= 6):
                    best_dir = min(valid_dirs, key=lambda d: abs((cur_c + d[0]) - p_c) + abs((cur_r + d[1]) - p_r))
                    self.current_dir = best_dir
                else:
                    # Geri dönmek yerine düz devam etmeyi tercih et
                    opp_dir = (-self.current_dir[0], -self.current_dir[1])
                    forward_dirs = [d for d in valid_dirs if d != opp_dir]
                    if forward_dirs:
                        self.current_dir = random.choice(forward_dirs)
                    else:
                        self.current_dir = random.choice(valid_dirs)

                self.target_c = cur_c + self.current_dir[0]
                self.target_r = cur_r + self.current_dir[1]
        else:
            self.x += (dx / dist) * step
            self.y += (dy / dist) * step

    def draw(self, surface):
        pulse = math.sin(self.anim_phase) * 2
        r = int(self.radius + pulse)
        # Kırmızı tehlikeli parıltı
        pygame.draw.circle(surface, (180, 20, 20), (int(self.x), int(self.y)), r + 3)
        pygame.draw.circle(surface, COLOR_ENEMY, (int(self.x), int(self.y)), r)
        # Gözler
        eye_offset = r * 0.35
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x - eye_offset), int(self.y - 2)), 3)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x + eye_offset), int(self.y - 2)), 3)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x - eye_offset), int(self.y - 2)), 1)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x + eye_offset), int(self.y - 2)), 1)


# ---------------------------------------------------------
# OYUNCU SINIFI
# ---------------------------------------------------------
class Player:
    def __init__(self, x, y, tile_size):
        self.x = float(x)
        self.y = float(y)
        self.tile_size = tile_size
        self.radius = tile_size * 0.34
        self.base_speed = 190.0
        self.speed = self.base_speed
        self.has_key = False
        self.shield_count = 0
        self.speed_boost_timer = 0.0
        self.invulnerable_timer = 0.0
        self.trail = []

    def update(self, dt, keys, maze_grid, cols, rows, doors):
        # Güçlendirme süreleri
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= dt
            self.speed = self.base_speed * 1.55
        else:
            self.speed = self.base_speed

        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt

        # Hareket girdisi (Ok tuşları + WASD)
        dx, dy = 0.0, 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1.0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1.0
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1.0

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        # Çarpışmalı hareket (X ve Y ayrı çözümlenir - kaygan duvar mantığı)
        new_x = self.x + dx * self.speed * dt
        if not self.check_wall_collision(new_x, self.y, maze_grid, cols, rows, doors):
            self.x = new_x

        new_y = self.y + dy * self.speed * dt
        if not self.check_wall_collision(self.x, new_y, maze_grid, cols, rows, doors):
            self.y = new_y

        # Kuyruk izi (Trail)
        if dx != 0 or dy != 0:
            self.trail.append((self.x, self.y, 0.25))
        for i in range(len(self.trail) - 1, -1, -1):
            x, y, t = self.trail[i]
            t -= dt
            if t <= 0:
                self.trail.pop(i)
            else:
                self.trail[i] = (x, y, t)

    def check_wall_collision(self, x, y, maze_grid, cols, rows, doors):
        check_points = [
            (x - self.radius, y - self.radius),
            (x + self.radius, y - self.radius),
            (x - self.radius, y + self.radius),
            (x + self.radius, y + self.radius),
        ]
        for px, py in check_points:
            c = int(px // self.tile_size)
            r = int(py // self.tile_size)
            if c < 0 or c >= cols or r < 0 or r >= rows:
                return True
            if maze_grid[r][c] == 1:
                return True
            # Kilitli kapı engeli
            if (c, r) in doors:
                return True
        return False

    def take_hit(self):
        """Hasar aldığında kalkan kontrolü veya can kaybı"""
        if self.invulnerable_timer > 0:
            return False  # Dokunulmazlık devrede

        if self.shield_count > 0:
            self.shield_count -= 1
            self.invulnerable_timer = 1.2
            return False  # Kalkan darbeyi engelledi

        self.invulnerable_timer = 1.8
        return True  # Can azalsın

    def draw(self, surface):
        # Hareket kuyruğu
        for tx, ty, t in self.trail:
            alpha = int((t / 0.25) * 80)
            trail_surf = pygame.Surface((int(self.radius * 2), int(self.radius * 2)), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (0, 200, 255, alpha), (int(self.radius), int(self.radius)), int(self.radius * 0.8))
            surface.blit(trail_surf, (tx - self.radius, ty - self.radius))

        # Yanıp sönme (Hasar dokunulmazlığı)
        if self.invulnerable_timer > 0 and int(self.invulnerable_timer * 10) % 2 == 0:
            return

        # Kalkan dairesi
        if self.shield_count > 0:
            pygame.draw.circle(surface, (100, 220, 255), (int(self.x), int(self.y)), int(self.radius + 6), 2)

        # Hız efekti halkası
        if self.speed_boost_timer > 0:
            pygame.draw.circle(surface, (255, 230, 80), (int(self.x), int(self.y)), int(self.radius + 4), 1)

        # Oyuncu gövdesi
        pygame.draw.circle(surface, COLOR_PLAYER, (int(self.x), int(self.y)), int(self.radius))
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), int(self.radius * 0.45))


# ---------------------------------------------------------
# OYUN YÖNETİCİSİ (ANA MOTOR)
# ---------------------------------------------------------
class MazeEscapeGame:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Labirentten Kaçış - Engeller ve Tehlikeler")
        self.clock = pygame.time.Clock()

        # Fontlar
        self.font_large = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 40, bold=True)
        self.font_mid = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 24, bold=True)
        self.font_small = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 16)

        # Durumlar: "MENU", "PLAY", "LEVEL_COMPLETE", "GAME_OVER", "VICTORY"
        self.state = "MENU"
        self.level = 1
        self.max_level = 6
        self.score = 0
        self.lives = 3
        self.level_time = 0.0

        # Dinamik oyun verileri
        self.particles = []
        self.spikes = []
        self.lasers = []
        self.enemies = []
        self.coins = []
        self.items = []  # ('speed' or 'shield', c, r)
        self.doors = set()
        self.key_pos = None
        self.exit_pos = (1, 1)

    def start_level(self, level_num):
        self.level = level_num
        self.level_time = 0.0

        # Seviyeye göre büyüyen labirent boyutu
        base_cols = 15 + (level_num - 1) * 4
        base_rows = 11 + (level_num - 1) * 2
        # Tek sayı olmalı
        self.cols = base_cols if base_cols % 2 == 1 else base_cols + 1
        self.rows = base_rows if base_rows % 2 == 1 else base_rows + 1

        # Tile boyutunu ekrana sığdıracak şekilde hesapla (Üstte HUD için 70px bırak)
        available_w = SCREEN_WIDTH - 40
        available_h = SCREEN_HEIGHT - 100
        self.tile_size = min(available_w // self.cols, available_h // self.rows)
        self.tile_size = max(18, min(44, self.tile_size))

        self.offset_x = (SCREEN_WIDTH - (self.cols * self.tile_size)) // 2
        self.offset_y = 80 + (available_h - (self.rows * self.tile_size)) // 2

        # Labirent oluştur
        self.maze = MazeGenerator.generate(self.cols, self.rows)

        # Başlangıç ve Çıkış pozisyonları
        self.player = Player(
            self.offset_x + 1.5 * self.tile_size,
            self.offset_y + 1.5 * self.tile_size,
            self.tile_size
        )
        self.exit_pos = (self.cols - 2, self.rows - 2)
        self.maze[self.exit_pos[1]][self.exit_pos[0]] = 0

        # Boş yolları topla (Engel & Eşya yerleştirmek için)
        empty_cells = []
        for r in range(1, self.rows - 1):
            for c in range(1, self.cols - 1):
                if self.maze[r][c] == 0:
                    if (c, r) != (1, 1) and (c, r) != self.exit_pos:
                        empty_cells.append((c, r))
        random.shuffle(empty_cells)

        # 1. Kilit ve Anahtar Sistemi (Seviye 2 ve sonrasında)
        self.doors.clear()
        self.key_pos = None
        if self.level >= 2 and empty_cells:
            # Çıkışın önündeki koridora veya rastgele bir boğaza kapı koy
            door_c, door_r = self.exit_pos[0], self.exit_pos[1] - 1
            if self.maze[door_r][door_c] == 0:
                self.doors.add((door_c, door_r))
            else:
                door_c, door_r = self.exit_pos[0] - 1, self.exit_pos[1]
                self.doors.add((door_c, door_r))

            # Anahtarı labirentin uzak bir yerine koy
            if empty_cells:
                self.key_pos = empty_cells.pop()

        # 2. Dikenli Tuzaklar (Spikes)
        self.spikes.clear()
        num_spikes = min(len(empty_cells) // 4, 3 + self.level * 2)
        for _ in range(num_spikes):
            if empty_cells:
                sc, sr = empty_cells.pop()
                self.spikes.append(SpikeTrap(sc, sr, self.tile_size, cycle_time=2.2, offset=random.uniform(0, 2.0)))

        # 3. Lazer Bariyerleri (Seviye 3 ve üzeri)
        self.lasers.clear()
        if self.level >= 3:
            num_lasers = min(self.level - 1, 4)
            for _ in range(num_lasers):
                if empty_cells:
                    lc, lr = empty_cells.pop()
                    # Komşu boş hücre varsa aralarına lazer ger
                    for dc, dr in [(1, 0), (0, 1)]:
                        nc, nr = lc + dc, lr + dr
                        if 0 <= nc < self.cols and 0 <= nr < self.rows and self.maze[nr][nc] == 0:
                            self.lasers.append(LaserBarrier(lc, lr, nc, nr, self.tile_size, cycle_time=3.2, offset=random.uniform(0, 3)))
                            break

        # 4. Devriye Düşmanlar (Seviye 2 ve üzeri)
        self.enemies.clear()
        if self.level >= 2:
            num_enemies = min(1 + (self.level - 2), 5)
            for _ in range(num_enemies):
                if empty_cells:
                    ec, er = empty_cells.pop()
                    ex = self.offset_x + ec * self.tile_size + self.tile_size // 2
                    ey = self.offset_y + er * self.tile_size + self.tile_size // 2
                    self.enemies.append(PatrollingEnemy(ex, ey, self.tile_size, speed=80 + self.level * 10))

        # 5. Altınlar (Coin)
        self.coins.clear()
        num_coins = 5 + self.level * 3
        for _ in range(num_coins):
            if empty_cells:
                self.coins.append(empty_cells.pop())

        # 6. Güçlendirme İksirleri (Kalkan & Hız)
        self.items.clear()
        if empty_cells and random.random() < 0.8:
            self.items.append(('shield', empty_cells.pop()))
        if empty_cells and random.random() < 0.8:
            self.items.append(('speed', empty_cells.pop()))

        self.particles.clear()

    def add_sparkles(self, x, y, color, count=12):
        for _ in range(count):
            angle = random.uniform(0, 6.28)
            spd = random.uniform(30, 120)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            life = random.uniform(0.3, 0.6)
            self.particles.append(Particle(x, y, color, vx, vy, life, size=random.randint(2, 4)))

    def handle_hit(self):
        if self.player.take_hit():
            self.lives -= 1
            self.add_sparkles(self.player.x, self.player.y, (255, 50, 50), count=25)
            if self.lives <= 0:
                self.state = "GAME_OVER"
        else:
            # Kalkan kırıldı efekti
            self.add_sparkles(self.player.x, self.player.y, (100, 220, 255), count=18)

    def update(self, dt):
        if self.state != "PLAY":
            return

        self.level_time += dt
        keys = pygame.key.get_pressed()

        # Oyuncu güncelle
        # Maze koordinatlarına göre kaydırılmış kapıları kontrol et
        self.player.update(dt, keys, self.maze, self.cols, self.rows, self.doors)

        # Oyuncunun labirent ızgara pozisyonu
        grid_px = self.player.x - self.offset_x
        grid_py = self.player.y - self.offset_y
        pc = int(grid_px // self.tile_size)
        pr = int(grid_py // self.tile_size)

        # 1. Anahtar Toplama
        if self.key_pos and (pc, pr) == self.key_pos and not self.player.has_key:
            self.player.has_key = True
            kx = self.offset_x + self.key_pos[0] * self.tile_size + self.tile_size // 2
            ky = self.offset_y + self.key_pos[1] * self.tile_size + self.tile_size // 2
            self.add_sparkles(kx, ky, COLOR_KEY, 20)
            self.doors.clear()  # Kapı kilidi açılır!
            self.score += 250

        # 2. Altın Toplama
        for i in range(len(self.coins) - 1, -1, -1):
            cc, cr = self.coins[i]
            if (pc, pr) == (cc, cr):
                cx = self.offset_x + cc * self.tile_size + self.tile_size // 2
                cy = self.offset_y + cr * self.tile_size + self.tile_size // 2
                self.add_sparkles(cx, cy, COLOR_COIN, 10)
                self.coins.pop(i)
                self.score += 100

        # 3. İksir Toplama
        for i in range(len(self.items) - 1, -1, -1):
            itype, (ic, ir) = self.items[i]
            if (pc, pr) == (ic, ir):
                ix = self.offset_x + ic * self.tile_size + self.tile_size // 2
                iy = self.offset_y + ir * self.tile_size + self.tile_size // 2
                if itype == 'shield':
                    self.player.shield_count = min(2, self.player.shield_count + 1)
                    self.add_sparkles(ix, iy, (100, 220, 255), 18)
                elif itype == 'speed':
                    self.player.speed_boost_timer = 6.0
                    self.add_sparkles(ix, iy, (255, 230, 80), 18)
                self.items.pop(i)
                self.score += 150

        # 4. Dikenli Tuzaklar
        for spike in self.spikes:
            spike.update(dt)
            if spike.is_active and (pc, pr) == (spike.c, spike.r):
                self.handle_hit()

        # 5. Lazer Bariyerleri
        for laser in self.lasers:
            laser.update(dt)
            # Lazer pozisyonunu dünya koordinatına çevir
            if laser.check_player_collision(grid_px, grid_py, self.player.radius):
                self.handle_hit()

        # 6. Düşmanlar
        for enemy in self.enemies:
            # Labirent içi koordinatta güncelle
            enemy.update(dt, self.maze, self.rows, self.cols, (grid_px, grid_py))
            # Oyuncu ile çarpışma (Dünya koordinatları)
            edx = (self.offset_x + enemy.x) - self.player.x
            edy = (self.offset_y + enemy.y) - self.player.y
            if math.hypot(edx, edy) < (self.player.radius + enemy.radius):
                self.handle_hit()

        # 7. Çıkışa Ulaşma Kontrolü
        if (pc, pr) == self.exit_pos:
            # Seviye Tamamlandı!
            time_bonus = max(0, int(1000 - self.level_time * 25))
            self.score += 500 + time_bonus
            if self.level >= self.max_level:
                self.state = "VICTORY"
            else:
                self.state = "LEVEL_COMPLETE"

        # 8. Parçacıklar
        for p in self.particles[:]:
            if not p.update(dt):
                self.particles.remove(p)

    def draw_hud(self):
        # Üst Panel Arka Planı
        hud_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 70)
        pygame.draw.rect(self.screen, (10, 12, 20), hud_rect)
        pygame.draw.line(self.screen, (35, 42, 60), (0, 70), (SCREEN_WIDTH, 70), 2)

        # Seviye
        lvl_surf = self.font_mid.render(f"SEVİYE: {self.level}/{self.max_level}", True, (255, 255, 255))
        self.screen.blit(lvl_surf, (25, 20))

        # Canlar (Kalpler)
        heart_text = "❤️ " * self.lives
        heart_surf = self.font_mid.render(f"CAN: {heart_text}", True, (255, 70, 90))
        self.screen.blit(heart_surf, (220, 20))

        # Skor
        score_surf = self.font_mid.render(f"SKOR: {self.score}", True, (255, 215, 0))
        self.screen.blit(score_surf, (480, 20))

        # Durum İkonları (Anahtar, Kalkan, Hız)
        status_x = 730
        if self.player.has_key:
            pygame.draw.circle(self.screen, COLOR_KEY, (status_x, 35), 10)
            k_txt = self.font_small.render("ANAHTAR OK", True, COLOR_KEY)
            self.screen.blit(k_txt, (status_x + 16, 26))
            status_x += 120

        if self.player.shield_count > 0:
            s_txt = self.font_small.render(f"KALKAN x{self.player.shield_count}", True, (100, 220, 255))
            self.screen.blit(s_txt, (status_x, 26))

    def draw_maze(self):
        # Labirent Zemin ve Duvarları Çiz
        for r in range(self.rows):
            for c in range(self.cols):
                rx = self.offset_x + c * self.tile_size
                ry = self.offset_y + r * self.tile_size
                rect = pygame.Rect(rx, ry, self.tile_size, self.tile_size)

                if self.maze[r][c] == 1:
                    # Duvar
                    pygame.draw.rect(self.screen, COLOR_WALL, rect)
                    pygame.draw.rect(self.screen, COLOR_WALL_OUTLINE, rect, width=1)
                else:
                    # Zemin
                    pygame.draw.rect(self.screen, COLOR_FLOOR, rect)

        # Çıkış Kapısı
        ex_x = self.offset_x + self.exit_pos[0] * self.tile_size
        ex_y = self.offset_y + self.exit_pos[1] * self.tile_size
        exit_rect = pygame.Rect(ex_x + 3, ex_y + 3, self.tile_size - 6, self.tile_size - 6)
        pygame.draw.rect(self.screen, COLOR_EXIT, exit_rect, border_radius=4)
        exit_lbl = self.font_small.render("ÇIKIŞ", True, (10, 30, 20))
        self.screen.blit(exit_lbl, exit_lbl.get_rect(center=exit_rect.center))

        # Kilitli Kapılar
        for dc, dr in self.doors:
            door_rect = pygame.Rect(self.offset_x + dc * self.tile_size + 2, self.offset_y + dr * self.tile_size + 2, self.tile_size - 4, self.tile_size - 4)
            pygame.draw.rect(self.screen, COLOR_DOOR, door_rect, border_radius=3)
            pygame.draw.line(self.screen, (255, 255, 255), door_rect.topleft, door_rect.bottomright, 2)
            pygame.draw.line(self.screen, (255, 255, 255), door_rect.bottomleft, door_rect.topright, 2)

        # Dikenli Tuzaklar
        for spike in self.spikes:
            # Spike çizimi dünya koordinatlarına kaydırılmış yüzeye aktarılır
            s_rect = pygame.Rect(self.offset_x + spike.rect.x, self.offset_y + spike.rect.y, spike.rect.width, spike.rect.height)
            temp_spike = SpikeTrap(0, 0, self.tile_size)
            temp_spike.rect = s_rect
            temp_spike.is_active = spike.is_active
            temp_spike.draw(self.screen)

        # Lazerler
        for laser in self.lasers:
            l_world = LaserBarrier(0, 0, 0, 0, self.tile_size)
            l_world.x1 = self.offset_x + laser.x1
            l_world.y1 = self.offset_y + laser.y1
            l_world.x2 = self.offset_x + laser.x2
            l_world.y2 = self.offset_y + laser.y2
            l_world.is_active = laser.is_active
            l_world.draw(self.screen)

        # Altınlar
        for cc, cr in self.coins:
            cx = self.offset_x + cc * self.tile_size + self.tile_size // 2
            cy = self.offset_y + cr * self.tile_size + self.tile_size // 2
            pygame.draw.circle(self.screen, COLOR_COIN, (cx, cy), max(3, int(self.tile_size * 0.22)))
            pygame.draw.circle(self.screen, (255, 255, 200), (cx - 1, cy - 1), max(1, int(self.tile_size * 0.08)))

        # İksirler / Güçlendiriciler
        for itype, (ic, ir) in self.items:
            ix = self.offset_x + ic * self.tile_size + self.tile_size // 2
            iy = self.offset_y + ir * self.tile_size + self.tile_size // 2
            if itype == 'shield':
                pygame.draw.circle(self.screen, (100, 220, 255), (ix, iy), max(4, int(self.tile_size * 0.28)))
            else:
                pygame.draw.circle(self.screen, (255, 230, 80), (ix, iy), max(4, int(self.tile_size * 0.28)))

        # Anahtar
        if self.key_pos and not self.player.has_key:
            kx = self.offset_x + self.key_pos[0] * self.tile_size + self.tile_size // 2
            ky = self.offset_y + self.key_pos[1] * self.tile_size + self.tile_size // 2
            pygame.draw.circle(self.screen, COLOR_KEY, (kx, ky), max(4, int(self.tile_size * 0.25)))
            pygame.draw.rect(self.screen, COLOR_KEY, (kx - 2, ky, 4, 8))

        # Düşmanlar
        for enemy in self.enemies:
            temp_enemy = PatrollingEnemy(self.offset_x + enemy.x, self.offset_y + enemy.y, self.tile_size)
            temp_enemy.radius = enemy.radius
            temp_enemy.anim_phase = enemy.anim_phase
            temp_enemy.draw(self.screen)

        # Sis / Görüş Kısıtlaması (Seviye 4 ve sonrası için Gerilim Modu)
        if self.level >= 4:
            fog = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            fog.fill((10, 12, 18, 240))
            # Oyuncu etrafında ışık çemberi aç
            torch_radius = int(self.tile_size * (3.8 - (self.level - 4) * 0.4))
            pygame.draw.circle(fog, (0, 0, 0, 0), (int(self.player.x), int(self.player.y)), torch_radius)
            pygame.draw.circle(fog, (255, 220, 100, 30), (int(self.player.x), int(self.player.y)), torch_radius)
            self.screen.blit(fog, (0, 0))

    def render(self):
        self.screen.fill(COLOR_BG)

        if self.state == "MENU":
            self.draw_menu_screen()
        elif self.state == "PLAY":
            self.draw_maze()
            self.player.draw(self.screen)
            for p in self.particles:
                p.draw(self.screen)
            self.draw_hud()
        elif self.state == "LEVEL_COMPLETE":
            self.draw_maze()
            self.draw_overlay_card("SEVİYE TAMAMLANDI! 🎉", f"Tebrikler! Skorun: {self.score}", "Devam etmek için [BOŞLUK] tuşuna bas")
        elif self.state == "GAME_OVER":
            self.draw_overlay_card("OYUN BİTTİ 💀", f"Canların tükendi! Toplam Skor: {self.score}", "Tekrar denemek için [BOŞLUK] tuşuna bas")
        elif self.state == "VICTORY":
            self.draw_overlay_card("BÜYÜK ZAFER! 🏆", f"Bütün labirentlerden kaçtın! Skor: {self.score}", "Yeniden oynamak için [BOŞLUK] tuşuna bas")

        pygame.display.flip()

    def draw_menu_screen(self):
        title = self.font_large.render("LABİRENTTEN KAÇIŞ", True, (0, 230, 255))
        subtitle = self.font_mid.render("Tuzaklar, Lazerler ve Muhafızlardan Kaç!", True, (200, 215, 240))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 180)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 235)))

        # Bilgi Kutusu
        box_rect = pygame.Rect(SCREEN_WIDTH // 2 - 250, 280, 500, 220)
        pygame.draw.rect(self.screen, (22, 28, 42), box_rect, border_radius=12)
        pygame.draw.rect(self.screen, (45, 55, 80), box_rect, width=2, border_radius=12)

        guides = [
            "🎮 Kontroller: Yön Tuşları veya W, A, S, D",
            "🔴 Engeller: Dikenli zeminler, yanıp sönen lazerler",
            "👾 Düşmanlar: Koridorda devriye gezen gardiyanlar",
            "🔑 Kilitli Kapılar: Çıkışı açmak için altın anahtarı bul",
            "🛡️ Güçlendiriciler: Mavi Kalkan ve Sarı Hız iksirleri",
        ]
        for idx, g in enumerate(guides):
            line = self.font_small.render(g, True, (220, 230, 245))
            self.screen.blit(line, (box_rect.x + 30, box_rect.y + 25 + idx * 36))

        prompt = self.font_mid.render("Başlamak için [BOŞLUK] veya [ENTER]'a bas", True, (50, 255, 126))
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, 550)))

    def draw_overlay_card(self, title_text, desc_text, action_text):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 12, 20, 180))
        self.screen.blit(overlay, (0, 0))

        card_rect = pygame.Rect(SCREEN_WIDTH // 2 - 260, SCREEN_HEIGHT // 2 - 140, 520, 260)
        pygame.draw.rect(self.screen, (22, 28, 44), card_rect, border_radius=14)
        pygame.draw.rect(self.screen, (60, 75, 110), card_rect, width=2, border_radius=14)

        t_surf = self.font_large.render(title_text, True, (255, 255, 255))
        d_surf = self.font_mid.render(desc_text, True, (220, 230, 255))
        a_surf = self.font_mid.render(action_text, True, (50, 255, 126))

        self.screen.blit(t_surf, t_surf.get_rect(center=(SCREEN_WIDTH // 2, card_rect.y + 60)))
        self.screen.blit(d_surf, d_surf.get_rect(center=(SCREEN_WIDTH // 2, card_rect.y + 125)))
        self.screen.blit(a_surf, a_surf.get_rect(center=(SCREEN_WIDTH // 2, card_rect.y + 195)))

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif self.state == "MENU" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.score = 0
                        self.lives = 3
                        self.start_level(1)
                        self.state = "PLAY"
                    elif self.state == "LEVEL_COMPLETE" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.start_level(self.level + 1)
                        self.state = "PLAY"
                    elif self.state in ("GAME_OVER", "VICTORY") and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.score = 0
                        self.lives = 3
                        self.start_level(1)
                        self.state = "PLAY"

            self.update(dt)
            self.render()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = MazeEscapeGame()
    game.run()
