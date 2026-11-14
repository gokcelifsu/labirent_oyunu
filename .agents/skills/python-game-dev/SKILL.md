---
name: python-game-dev
description: >-
  Expert Python game development workflow using Pygame/Pygame-CE.
  Use when designing, building, debugging, or extending 2D Python games,
  including game architecture, state machines, sprite management, collision detection,
  procedural audio/graphics, and performance optimization.
---

# Python Game Development Skill (Pygame / 2D)

This skill guides the agent in building robust, performant, and well-structured 2D games in Python using Pygame / Pygame-CE.

---

## 1. Core Architecture Principles

Always design Python games using modular and clean separation of concerns:

1. **State Machine / Scene Management**:
   - Separate scenes into distinct states: `MenuState`, `PlayState`, `PauseState`, `GameOverState`.
   - The main engine loop delegates `update(dt)`, `draw(screen)`, and `handle_event(event)` to the active state.

2. **Fixed / Delta-Time Game Loop**:
   - Always calculate delta time (`dt = clock.tick(FPS) / 1000.0`) to decouple movement/physics from frame rate.
   - Cap maximum delta time to prevent tunneling during lag spikes (e.g., `dt = min(dt, 0.05)`).

3. **Fallback & Procedural Asset Rendering**:
   - Never let a missing `.png` or `.wav` crash the game.
   - If external assets are missing, use procedural rendering (`pygame.draw.rect`, `pygame.draw.circle`, `pygame.Surface` with alpha) and generate synthetic sound effects or beeps via `pygame.sndarray` / `wave`.

4. **Sprite & Group Architecture**:
   - Inherit from `pygame.sprite.Sprite`.
   - Organize into logical groups: `all_sprites`, `enemies`, `projectiles`, `collectables`, `obstacles`.
   - Leverage `pygame.sprite.groupcollide` and `pygame.sprite.spritecollide` for optimized collision passes.

---

## 2. Standard Engine Skeleton

```python
import sys
import pygame

class Game:
    def __init__(self, title="Python Game", width=800, height=600, fps=60):
        pygame.init()
        pygame.font.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass  # Audio device not available
            
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.fps = fps
        self.running = True
        self.states = {}
        self.current_state = None

    def change_state(self, state_name):
        if state_name in self.states:
            self.current_state = self.states[state_name]
            self.current_state.enter()

    def run(self):
        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0
            dt = min(dt, 0.05)  # Cap delta time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif self.current_state:
                    self.current_state.handle_event(event)

            if self.current_state:
                self.current_state.update(dt)
                self.current_state.draw(self.screen)

            pygame.display.flip()

        pygame.quit()
        sys.exit()
```

---

## 3. Best Practices & Verification

- **Window Close Handling**: Always catch `pygame.QUIT` and trigger clean exit without leaving orphan processes.
- **Responsive Controls**: Support both Arrow keys and WASD. For actions, support Space and Mouse clicks.
- **Audio Graceful Degradation**: Wrap audio calls inside try/except blocks so headless or audio-less environments do not crash.
- **Smooth Movement**: Store player coordinates as `float` variables (`self.x`, `self.y`) and update `self.rect.topleft = (round(self.x), round(self.y))` for sub-pixel accuracy.
