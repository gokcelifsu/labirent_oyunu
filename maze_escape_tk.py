"""
Labirentten Kaçış - Alev Fırtınası (Flame Maze Escape)
Hızlı akış, 60 FPS, detaylı labirentler, alev püskürteçleri ve uçan ateş topları!
Harici kütüphane gerektirmez (Standart Tkinter).
"""

import tkinter as tk
import random
import math
import time

CANVAS_WIDTH = 980
CANVAS_HEIGHT = 680

# Renkler
COLOR_BG = "#0b0e14"
COLOR_FLOOR = "#131822"
COLOR_FLOOR_ALT = "#161d2a"
COLOR_WALL = "#1e2638"
COLOR_WALL_TOP = "#2d374d"
COLOR_WALL_BORDER = "#404d6b"

COLOR_PLAYER = "#00e5ff"
COLOR_PLAYER_CORE = "#ffffff"
COLOR_EXIT = "#00ff88"

# Alev Renkleri
FIRE_COLORS = ["#ff2200", "#ff5500", "#ff8800", "#ffcc00", "#ffffff"]


class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=3):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        return self.life > 0


class FirePit:
    """Zeminde periyodik olarak alev püskürten ateş tuzağı"""
    def __init__(self, c, r, cycle=2.0, offset=0.0):
        self.c = c
        self.r = r
        self.cycle = cycle
        self.timer = offset % cycle
        # Aşama: 0 -> Uyuyan köz, 1 -> Uyarı kıvılcımı, 2 -> Devasa Alev (Ölümcül)
        self.state = 0

    def update(self, dt):
        self.timer = (self.timer + dt) % self.cycle
        norm = self.timer / self.cycle
        if norm < 0.45:
            self.state = 0  # Sönük
        elif norm < 0.60:
            self.state = 1  # Uyarı (küçük alev/kıvılcım)
        else:
            self.state = 2  # Aktif Şiddetli Alev! (HASAR VERİR)


class Fireball:
    """Koridorlarda hızla uçan ve duvardan seken alev topu"""
    def __init__(self, x, y, dx, dy, speed=160):
        self.x = float(x)
        self.y = float(y)
        self.dx = dx
        self.dy = dy
        self.speed = speed
        self.radius = 8

    def update(self, dt, maze, cols, rows, tile_size, offset_x, offset_y):
        step_x = self.dx * self.speed * dt
        step_y = self.dy * self.speed * dt

        next_x = self.x + step_x
        next_y = self.y + step_y

        gc = int((next_x - offset_x) // tile_size)
        gr = int((next_y - offset_y) // tile_size)

        # Çarpışma kontrolü
        if 0 <= gc < cols and 0 <= gr < rows and maze[gr][gc] == 0:
            self.x = next_x
            self.y = next_y
        else:
            # Duvardan sek
            self.dx = -self.dx
            self.dy = -self.dy
            self.x += self.dx * self.speed * dt
            self.y += self.dy * self.speed * dt


class TkFastFlameMaze:
    def __init__(self, root):
        self.root = root
        self.root.title("Labirentten Kaçış - Ateş Fırtınası")
        self.root.geometry(f"{CANVAS_WIDTH}x{CANVAS_HEIGHT + 60}")
        self.root.resizable(False, False)

        # Üst Panel (HUD)
        self.hud_frame = tk.Frame(root, bg="#080a0f", height=50)
        self.hud_frame.pack(fill=tk.X, side=tk.TOP)

        self.lbl_level = tk.Label(self.hud_frame, text="SEVİYE: 1/5", font=("Segoe UI", 12, "bold"), fg="#00e5ff", bg="#080a0f")
        self.lbl_level.pack(side=tk.LEFT, padx=18, pady=10)

        self.lbl_lives = tk.Label(self.hud_frame, text="CAN: ❤️ ❤️ ❤️", font=("Segoe UI", 12, "bold"), fg="#ff4466", bg="#080a0f")
        self.lbl_lives.pack(side=tk.LEFT, padx=18, pady=10)

        self.lbl_score = tk.Label(self.hud_frame, text="SKOR: 0", font=("Segoe UI", 12, "bold"), fg="#ffcc00", bg="#080a0f")
        self.lbl_score.pack(side=tk.LEFT, padx=18, pady=10)

        self.lbl_status = tk.Label(self.hud_frame, text="", font=("Segoe UI", 11, "bold"), fg="#00ff88", bg="#080a0f")
        self.lbl_status.pack(side=tk.RIGHT, padx=18, pady=10)

        # Tuval
        self.canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg=COLOR_BG, highlightthickness=0)
        self.canvas.pack()

        # Klavye
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.pressed_keys = set()

        # Oyun Durumu
        self.state = "MENU"
        self.level = 1
        self.max_level = 5
        self.score = 0
        self.lives = 3
        self.has_key = False
        self.invulnerable = 0.0

        # Oyuncu & Hız Ayarları (Hızlı ve Akıcı Hareket!)
        self.px = 0.0
        self.py = 0.0
        self.player_speed = 280.0  # Piksel/saniye (Eskiye göre neredeyse 2 kat daha hızlı!)
        self.player_radius = 8.0

        # Labirent
        self.maze = []
        self.cols = 21
        self.rows = 15
        self.tile_size = 28
        self.offset_x = 0
        self.offset_y = 0
        self.exit_pos = (1, 1)
        self.key_pos = None
        self.doors = set()
        self.coins = set()

        # Ateş Engelleri & Efektler
        self.fire_pits = []
        self.fireballs = []
        self.particles = []
        self.last_time = time.time()
        self.anim_frame = 0

        self.draw_menu()
        self.game_loop()

    def generate_detailed_maze(self, cols, rows):
        """Detaylı, çok kollu ve genişletilmiş labirent üretici"""
        grid = [[1 for _ in range(cols)] for _ in range(rows)]

        def neighbors(r, c):
            res = []
            for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                nr, nc = r + dr, c + dc
                if 1 <= nr < rows - 1 and 1 <= nc < cols - 1:
                    if grid[nr][nc] == 1:
                        res.append((nr, nc, dr, dc))
            return res

        grid[1][1] = 0
        stack = [(1, 1)]

        while stack:
            cr, cc = stack[-1]
            nbrs = neighbors(cr, cc)
            if nbrs:
                nr, nc, dr, dc = random.choice(nbrs)
                grid[cr + dr // 2][cc + dc // 2] = 0
                grid[nr][nc] = 0
                stack.append((nr, nc))
            else:
                stack.pop()

        # Çoklu yol ve alternatif rotalar aç (Oyuncunun akıcı kaçabilmesi için)
        extra_loops = (cols * rows) // 25
        for _ in range(extra_loops):
            er = random.randrange(2, rows - 2)
            ec = random.randrange(2, cols - 2)
            if grid[er][ec] == 1:
                # İki zıt taraf boşsa duvarı del
                if (grid[er - 1][ec] == 0 and grid[er + 1][ec] == 0) or \
                   (grid[er][ec - 1] == 0 and grid[er][ec + 1] == 0):
                    grid[er][ec] = 0

        return grid

    def start_level(self, lvl):
        self.level = lvl
        # Labirent boyutları her seviyede daha detaylı ve geniş
        self.cols = 21 + (lvl - 1) * 4  # 21, 25, 29, 33, 37
        self.rows = 15 + (lvl - 1) * 2  # 15, 17, 19, 21, 23
        if self.cols % 2 == 0: self.cols += 1
        if self.rows % 2 == 0: self.rows += 1

        # Tile boyutunu ekrana göre dinamik uyarla
        avail_w = CANVAS_WIDTH - 40
        avail_h = CANVAS_HEIGHT - 40
        self.tile_size = min(avail_w // self.cols, avail_h // self.rows)
        self.tile_size = max(18, min(38, self.tile_size))

        self.offset_x = (CANVAS_WIDTH - self.cols * self.tile_size) // 2
        self.offset_y = (CANVAS_HEIGHT - self.rows * self.tile_size) // 2
        self.player_radius = self.tile_size * 0.32

        self.maze = self.generate_detailed_maze(self.cols, self.rows)

        # Oyuncu konumu
        self.px = self.offset_x + 1.5 * self.tile_size
        self.py = self.offset_y + 1.5 * self.tile_size

        # Çıkış konumu
        self.exit_pos = (self.cols - 2, self.rows - 2)
        self.maze[self.exit_pos[1]][self.exit_pos[0]] = 0

        # Boş koridor hücrelerini topla
        empty_cells = []
        for r in range(1, self.rows - 1):
            for c in range(1, self.cols - 1):
                if self.maze[r][c] == 0 and (c, r) != (1, 1) and (c, r) != self.exit_pos:
                    empty_cells.append((c, r))
        random.shuffle(empty_cells)

        # Kilitli Kapı ve Anahtar (Seviye 2+)
        self.doors.clear()
        self.key_pos = None
        self.has_key = False
        if self.level >= 2 and empty_cells:
            # Çıkışın önündeki koridora kapı
            dc, dr = self.exit_pos[0], self.exit_pos[1] - 1
            if self.maze[dr][dc] == 0:
                self.doors.add((dc, dr))
            else:
                self.doors.add((self.exit_pos[0] - 1, self.exit_pos[1]))
            self.key_pos = empty_cells.pop()

        # ATEŞ ENGELLERİ 1: Alev Püskürteçleri (Fire Pits)
        self.fire_pits.clear()
        num_pits = 4 + self.level * 4  # Her seviyede daha fazla ateş tuzağı
        for _ in range(num_pits):
            if empty_cells:
                fc, fr = empty_cells.pop()
                cycle = random.uniform(1.6, 2.4)
                offset = random.uniform(0, 2.0)
                self.fire_pits.append(FirePit(fc, fr, cycle, offset))

        # ATEŞ ENGELLERİ 2: Uçan Ateş Topları (Bouncing Fireballs)
        self.fireballs.clear()
        num_fireballs = min(self.level + 1, 6)
        for _ in range(num_fireballs):
            if empty_cells:
                fbc, fbr = empty_cells.pop()
                fx = self.offset_x + fbc * self.tile_size + self.tile_size // 2
                fy = self.offset_y + fbr * self.tile_size + self.tile_size // 2
                dir_x, dir_y = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
                self.fireballs.append(Fireball(fx, fy, dir_x, dir_y, speed=130 + self.level * 25))

        # Altınlar
        self.coins.clear()
        num_coins = 8 + self.level * 4
        for _ in range(num_coins):
            if empty_cells:
                self.coins.add(empty_cells.pop())

        self.particles.clear()
        self.update_hud()

    def update_hud(self):
        self.lbl_level.config(text=f"SEVİYE: {self.level}/{self.max_level}")
        self.lbl_lives.config(text="CAN: " + ("❤️ " * max(0, self.lives)))
        self.lbl_score.config(text=f"SKOR: {self.score}")
        if self.has_key:
            self.lbl_status.config(text="🔑 ALTIN ANAHTAR ALINDI! (KAPI AÇIK)", fg="#ffcc00")
        else:
            self.lbl_status.config(text="🔥 ALEVLERDEN KAÇ VE ÇIKIŞA ULAŞ!", fg="#ff5500")

    def add_fire_particles(self, x, y, count=8):
        for _ in range(count):
            angle = random.uniform(0, 6.28)
            spd = random.uniform(1.5, 4.5)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd - 1.2  # Alevler yukarı yükselir
            life = random.randint(8, 20)
            col = random.choice(FIRE_COLORS)
            self.particles.append(Particle(x, y, vx, vy, col, life, size=random.randint(2, 5)))

    def take_hit(self):
        if self.invulnerable > 0:
            return
        self.lives -= 1
        self.invulnerable = 1.4  # Saniye boyunca dokunulmazlık
        self.add_fire_particles(self.px, self.py, 30)
        self.update_hud()
        if self.lives <= 0:
            self.state = "GAME_OVER"

    def on_key_press(self, event):
        k = event.keysym.lower()
        self.pressed_keys.add(k)
        if self.state == "MENU" and k in ("space", "return"):
            self.score = 0
            self.lives = 3
            self.start_level(1)
            self.state = "PLAY"
        elif self.state == "LEVEL_COMPLETE" and k in ("space", "return"):
            self.start_level(self.level + 1)
            self.state = "PLAY"
        elif self.state in ("GAME_OVER", "VICTORY") and k in ("space", "return"):
            self.score = 0
            self.lives = 3
            self.start_level(1)
            self.state = "PLAY"

    def on_key_release(self, event):
        k = event.keysym.lower()
        if k in self.pressed_keys:
            self.pressed_keys.remove(k)

    def is_walkable(self, x, y):
        r = self.player_radius
        # 4 köşe kontrolü
        for cx, cy in [(x - r, y - r), (x + r, y - r), (x - r, y + r), (x + r, y + r)]:
            gc = int((cx - self.offset_x) // self.tile_size)
            gr = int((cy - self.offset_y) // self.tile_size)
            if gc < 0 or gc >= self.cols or gr < 0 or gr >= self.rows:
                return False
            if self.maze[gr][gc] == 1:
                return False
            if (gc, gr) in self.doors:
                return False
        return True

    def update_game(self, dt):
        if self.state != "PLAY":
            return

        if self.invulnerable > 0:
            self.invulnerable -= dt

        # Hızlı ve Akıcı Hareket
        dx, dy = 0.0, 0.0
        if "up" in self.pressed_keys or "w" in self.pressed_keys: dy -= 1.0
        if "down" in self.pressed_keys or "s" in self.pressed_keys: dy += 1.0
        if "left" in self.pressed_keys or "a" in self.pressed_keys: dx -= 1.0
        if "right" in self.pressed_keys or "d" in self.pressed_keys: dx += 1.0

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        # X ve Y eksenlerini ayrı test ederek duvara takılmadan akıcı kayma
        step = self.player_speed * dt
        if dx != 0:
            nx = self.px + dx * step
            if self.is_walkable(nx, self.py):
                self.px = nx
        if dy != 0:
            ny = self.py + dy * step
            if self.is_walkable(self.px, ny):
                self.py = ny

        cur_c = int((self.px - self.offset_x) // self.tile_size)
        cur_r = int((self.py - self.offset_y) // self.tile_size)

        # Altın toplama
        if (cur_c, cur_r) in self.coins:
            self.coins.remove((cur_c, cur_r))
            self.score += 150
            self.update_hud()

        # Anahtar toplama
        if self.key_pos and (cur_c, cur_r) == self.key_pos and not self.has_key:
            self.has_key = True
            self.doors.clear()
            self.score += 400
            self.add_fire_particles(self.px, self.py, 20)
            self.update_hud()

        # ATEŞ TUZAKLARI GÜNCELLEME
        for pit in self.fire_pits:
            pit.update(dt)
            # Eğer ateş püskürüyorsa ve oyuncu bu hücredeyse hasar al!
            if pit.state == 2 and (cur_c, cur_r) == (pit.c, pit.r):
                self.take_hit()

            # Alev efekti parçacıkları
            if pit.state >= 1 and random.random() < 0.35:
                fx = self.offset_x + pit.c * self.tile_size + self.tile_size // 2
                fy = self.offset_y + pit.r * self.tile_size + self.tile_size // 2
                self.add_fire_particles(fx, fy, 2 if pit.state == 1 else 5)

        # UÇAN ATEŞ TOPLARI GÜNCELLEME
        for fb in self.fireballs:
            fb.update(dt, self.maze, self.cols, self.rows, self.tile_size, self.offset_x, self.offset_y)
            # Alev kuyruk parçacığı
            if random.random() < 0.6:
                self.add_fire_particles(fb.x, fb.y, 2)
            # Çarpışma kontrolü
            dist = math.hypot(fb.x - self.px, fb.y - self.py)
            if dist < (self.player_radius + fb.radius):
                self.take_hit()

        # Parçacıklar
        for p in self.particles[:]:
            if not p.update():
                self.particles.remove(p)

        # ÇIKIŞA ULAŞMA
        if (cur_c, cur_r) == self.exit_pos:
            self.score += 600 + self.level * 200
            if self.level >= self.max_level:
                self.state = "VICTORY"
            else:
                self.state = "LEVEL_COMPLETE"
            self.update_hud()

    def draw_game(self):
        self.canvas.delete("all")
        self.anim_frame += 1

        # 1. Labirent Zemin ve Duvarları (Detaylı Tasarım)
        ts = self.tile_size
        for r in range(self.rows):
            for c in range(self.cols):
                x1 = self.offset_x + c * ts
                y1 = self.offset_y + r * ts
                x2 = x1 + ts
                y2 = y1 + ts

                if self.maze[r][c] == 1:
                    # Derinlikli Duvar (Üst Kenar açık renk, Gövde koyu)
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=COLOR_WALL, outline="")
                    self.canvas.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y1 + 4, fill=COLOR_WALL_TOP, outline="")
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="", outline=COLOR_WALL_BORDER, width=1)
                else:
                    # Detaylı Karo Zemin
                    bg_col = COLOR_FLOOR if (c + r) % 2 == 0 else COLOR_FLOOR_ALT
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_col, outline="")

        # 2. ATEŞ PÜSKÜRTEÇLERİ (Fire Pits)
        for pit in self.fire_pits:
            px1 = self.offset_x + pit.c * ts + 2
            py1 = self.offset_y + pit.r * ts + 2
            px2 = px1 + ts - 4
            py2 = py1 + ts - 4

            if pit.state == 0:
                # Sönük Köz / Izgara
                self.canvas.create_rectangle(px1, py1, px2, py2, fill="#2a1208", outline="#441a0e", width=1)
                self.canvas.create_line(px1, py1 + ts // 2, px2, py1 + ts // 2, fill="#552210")
            elif pit.state == 1:
                # Uyarı Kıvılcımları & Duman
                self.canvas.create_rectangle(px1, py1, px2, py2, fill="#5a1805", outline="#ff5500", width=2)
                self.canvas.create_oval(px1 + 4, py1 + 4, px2 - 4, py2 - 4, fill="#ff8800", outline="")
            else:
                # ŞİDDETLİ PARLAYAN ALEV SÜTUNU (Ateş Efekti)
                f_color = random.choice(["#ff2200", "#ff5500", "#ff8800", "#ffcc00"])
                self.canvas.create_rectangle(px1, py1, px2, py2, fill=f_color, outline="#ffffff", width=2)
                # Alev Şekli
                flame_pts = [
                    px1 + ts * 0.2, py2,
                    px1 + ts * 0.5, py1 - random.randint(2, 6),
                    px1 + ts * 0.8, py2
                ]
                self.canvas.create_polygon(flame_pts, fill="#ffdd00", outline="#ffffff")

        # 3. Kilitli Kapı
        for dc, dr in self.doors:
            dx1 = self.offset_x + dc * ts + 2
            dy1 = self.offset_y + dr * ts + 2
            self.canvas.create_rectangle(dx1, dy1, dx1 + ts - 4, dy1 + ts - 4, fill="#7928ca", outline="#b86bff", width=2)
            self.canvas.create_text(dx1 + ts // 2, dy1 + ts // 2, text="🔒", font=("Segoe UI", int(ts * 0.45)))

        # 4. Altın Anahtar
        if self.key_pos and not self.has_key:
            kx = self.offset_x + self.key_pos[0] * ts + ts // 2
            ky = self.offset_y + self.key_pos[1] * ts + ts // 2
            self.canvas.create_text(kx, ky, text="🔑", font=("Segoe UI", int(ts * 0.55)))

        # 5. Altınlar (Puan Kristalleri)
        for cc, cr in self.coins:
            cx = self.offset_x + cc * ts + ts // 2
            cy = self.offset_y + cr * ts + ts // 2
            r_coin = max(3, ts * 0.22)
            self.canvas.create_oval(cx - r_coin, cy - r_coin, cx + r_coin, cy + r_coin, fill="#ffcc00", outline="#ff9900")

        # 6. ÇIKIŞ KAPISI (Parlayan Enerji Portalı)
        ex_x = self.offset_x + self.exit_pos[0] * ts
        ex_y = self.offset_y + self.exit_pos[1] * ts
        self.canvas.create_rectangle(ex_x + 2, ex_y + 2, ex_x + ts - 2, ex_y + ts - 2, fill="#003822", outline="#00ff88", width=2)
        portal_pulse = 2 + (self.anim_frame % 6)
        self.canvas.create_oval(ex_x + portal_pulse, ex_y + portal_pulse, ex_x + ts - portal_pulse, ex_y + ts - portal_pulse, fill="#00ff88", outline="")
        self.canvas.create_text(ex_x + ts // 2, ex_y + ts // 2, text="ÇIKIŞ", font=("Segoe UI", int(ts * 0.3), "bold"), fill="#000000")

        # 7. UÇAN ATEŞ TOPLARI
        for fb in self.fireballs:
            self.canvas.create_oval(fb.x - fb.radius - 2, fb.y - fb.radius - 2, fb.x + fb.radius + 2, fb.y + fb.radius + 2, fill="#ff2200", outline="")
            self.canvas.create_oval(fb.x - fb.radius, fb.y - fb.radius, fb.x + fb.radius, fb.y + fb.radius, fill="#ff8800", outline="")
            self.canvas.create_oval(fb.x - fb.radius * 0.5, fb.y - fb.radius * 0.5, fb.x + fb.radius * 0.5, fb.y + fb.radius * 0.5, fill="#ffea00", outline="")

        # 8. Parçacıklar (Alev Kıvılcımları)
        for p in self.particles:
            self.canvas.create_oval(p.x - p.size, p.y - p.size, p.x + p.size, p.y + p.size, fill=p.color, outline="")

        # 9. OYUNCU (Neon Mavi & Akıcı Parıltı)
        pr = self.player_radius
        if self.invulnerable <= 0 or (int(self.invulnerable * 15) % 2 == 0):
            # Dış Parlama
            self.canvas.create_oval(self.px - pr - 3, self.py - pr - 3, self.px + pr + 3, self.py + pr + 3, outline="#00e5ff", width=1)
            # Gövde
            self.canvas.create_oval(self.px - pr, self.py - pr, self.px + pr, self.py + pr, fill=COLOR_PLAYER, outline="#ffffff", width=1)
            # Çekirdek
            self.canvas.create_oval(self.px - pr * 0.4, self.py - pr * 0.4, self.px + pr * 0.4, self.py + pr * 0.4, fill=COLOR_PLAYER_CORE, outline="")

    def draw_menu(self):
        self.canvas.delete("all")
        self.canvas.create_text(CANVAS_WIDTH // 2, 160, text="🔥 LABİRENTTEN KAÇIŞ: ATEŞ FIRTINASI 🔥", font=("Segoe UI", 28, "bold"), fill="#ff5500")
        self.canvas.create_text(CANVAS_WIDTH // 2, 210, text="Hızlı Akış • Alev Püskürteçleri • Uçan Ateş Topları", font=("Segoe UI", 15), fill="#ffcc00")

        # Bilgi Kartı
        bx1, by1 = CANVAS_WIDTH // 2 - 270, 250
        bx2, by2 = CANVAS_WIDTH // 2 + 270, 480
        self.canvas.create_rectangle(bx1, by1, bx2, by2, fill="#131822", outline="#ff5500", width=2)

        guides = [
            "⚡ Hız Arttırıldı: Anında tepki veren hızlı hareket mekaniği",
            "🔥 Alev Püskürteçleri: Yanıp sönen ateş tuzaklarına dikkat et!",
            "☄️ Uçan Ateş Topları: Koridorlarda seken ateş toplarından sıyrıl!",
            "🔑 Altın Anahtar: Kilitli kapıları açmak için anahtarı kap!",
            "🟢 Çıkış Portalı: Labirentten kaçıp sonraki seviyeye geç!",
        ]
        for i, g in enumerate(guides):
            self.canvas.create_text(bx1 + 25, by1 + 35 + i * 40, text=g, anchor="w", font=("Segoe UI", 12), fill="#e6edf3")

        self.canvas.create_text(CANVAS_WIDTH // 2, 550, text="BAŞLAMAK İÇİN [BOŞLUK] TUŞUNA BASIN", font=("Segoe UI", 18, "bold"), fill="#00ff88")

    def draw_card(self, title, desc, prompt, color="#00e5ff"):
        cx1, cy1 = CANVAS_WIDTH // 2 - 280, CANVAS_HEIGHT // 2 - 140
        cx2, cy2 = CANVAS_WIDTH // 2 + 280, CANVAS_HEIGHT // 2 + 140
        self.canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="#0d1117", outline=color, width=3)
        self.canvas.create_text(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2 - 60, text=title, font=("Segoe UI", 24, "bold"), fill=color)
        self.canvas.create_text(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2, text=desc, font=("Segoe UI", 15), fill="#ffffff")
        self.canvas.create_text(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2 + 75, text=prompt, font=("Segoe UI", 16, "bold"), fill="#00ff88")

    def game_loop(self):
        cur_time = time.time()
        dt = cur_time - self.last_time
        self.last_time = cur_time
        dt = min(dt, 0.05)  # Cap delta time

        if self.state == "PLAY":
            self.update_game(dt)
            self.draw_game()
        elif self.state == "LEVEL_COMPLETE":
            self.draw_card("SEVİYE TAMAMLANDI! 🎉", f"Alevlerden kurtuldun! Toplam Skor: {self.score}", "Sonraki seviye için [BOŞLUK]'a bas", "#00ff88")
        elif self.state == "GAME_OVER":
            self.draw_card("ATEŞTE YANDIN! 💀", f"Alevler seni yakaladı! Skorun: {self.score}", "Yeniden denemek için [BOŞLUK]'a bas", "#ff2200")
        elif self.state == "VICTORY":
            self.draw_card("EFSANEVİ KAÇIŞ! 🏆", f"Bütün alev fırtınasını aştın! Skorun: {self.score}", "Tekrar oynamak için [BOŞLUK]'a bas", "#ffcc00")

        # 60 FPS (yaklaşık 16 ms)
        self.root.after(16, self.game_loop)


if __name__ == "__main__":
    root = tk.Tk()
    app = TkFastFlameMaze(root)
    root.mainloop()
