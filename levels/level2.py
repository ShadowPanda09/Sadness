# level2.py
import pygame
import sys
import random
import math
import time

# --- Constants ---
V_WIDTH, V_HEIGHT = 640, 480
PLAYER_SIZE = 32
FPS = 60

# Dash
DASH_SPEED = 30
DASH_FRAMES = 3
DASH_COOLDOWN = 400
AFTERIMAGE_LIFETIME = 250
BORDER_THICKNESS = 5

# Health / damage
PLAYER_MAX_HEALTH = 100

# Effects
HIT_FLASH_DURATION = 150
PULSE_DURATION = 500
PULSE_ALPHA = 100

# Colors
NEON_COLORS = [
    ((0, 255, 180), (0, 100, 70)),
    ((0, 200, 255), (0, 80, 100)),
    ((140, 0, 255), (80, 0, 120)),
    ((0, 255, 120), (0, 100, 50)),
]

class AfterImage:
    def __init__(self, pos, order, total):
        x = max(pos[0], BORDER_THICKNESS + PLAYER_SIZE / 2)
        x = min(x, V_WIDTH - BORDER_THICKNESS - PLAYER_SIZE / 2)
        y = max(pos[1], BORDER_THICKNESS + PLAYER_SIZE / 2)
        y = min(y, V_HEIGHT - BORDER_THICKNESS - PLAYER_SIZE / 2)
        self.pos = (x, y)
        self.created_at = pygame.time.get_ticks()
        self.order = order
        self.total = total

    def get_alpha(self):
        elapsed = pygame.time.get_ticks() - self.created_at
        if elapsed > AFTERIMAGE_LIFETIME:
            return 0
        base_alpha = 50 + int(205 * (self.order / self.total))
        fade_factor = 1 - elapsed / AFTERIMAGE_LIFETIME
        return int(base_alpha * fade_factor)


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.health = PLAYER_MAX_HEALTH
        self.dead = False
        self.hit_flash = False
        self.hit_time = 0

        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(self.rect.center)
        self.speed = 3

        # Dash
        self.dash_cooldown = DASH_COOLDOWN
        self.last_dash = -DASH_COOLDOWN
        self.is_dashing = False
        self.dash_dir = pygame.Vector2(0, -1)
        self.dash_start_time = 0
        self.dash_progress = 0
        self.afterimages = []
        self._next_afterimage_at = 0
        self.dash_key_pressed = False

        # Facing vector
        self.facing = pygame.Vector2(0, -1)

    def take_damage(self, amount):
        if self.dead:
            return
        self.health -= amount
        self.hit_flash = True
        self.hit_time = pygame.time.get_ticks()
        if self.health <= 0:
            self.health = 0
            self.dead = True

    def try_start_dash(self):
        now = pygame.time.get_ticks()
        if self.dead or self.is_dashing or (now - self.last_dash < self.dash_cooldown):
            return
        self.dash_dir = self.facing.normalize() if self.facing.length_squared() > 0 else pygame.Vector2(0, -1)
        self.is_dashing = True
        self.dash_start_time = now
        self.last_dash = now
        self._next_afterimage_at = now
        self.afterimages.clear()
        self.afterimages.append(AfterImage(self.pos, 1, DASH_FRAMES))

    def update_dash(self):
        if not self.is_dashing:
            return
        now = pygame.time.get_ticks()
        self.pos += self.dash_dir * DASH_SPEED
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        if now >= self._next_afterimage_at and len(self.afterimages) < DASH_FRAMES:
            self.afterimages.append(AfterImage(self.pos, len(self.afterimages)+1, DASH_FRAMES))
            self._next_afterimage_at = now + (self.dash_cooldown // DASH_FRAMES)
        self.dash_progress += 1
        if self.dash_progress >= DASH_FRAMES:
            self.is_dashing = False
            self.dash_progress = 0
            self.afterimages.clear()

    def update(self, keys, bounds_rect):
        if self.dead:
            return

        # Movement - no diagonals
        move_vec = pygame.Vector2(0, 0)
        if not self.is_dashing:
            if keys[pygame.K_w]:
                move_vec.y = -1
            elif keys[pygame.K_s]:
                move_vec.y = 1
            elif keys[pygame.K_a]:
                move_vec.x = -1
            elif keys[pygame.K_d]:
                move_vec.x = 1

            if move_vec.length_squared() > 0:
                move_vec = move_vec.normalize() * self.speed
                self.facing = move_vec.normalize()
                self.pos += move_vec
                self.rect.center = (int(self.pos.x), int(self.pos.y))
                self.rect.clamp_ip(bounds_rect)
                self.pos = pygame.Vector2(self.rect.center)

        # Dash
        if keys[pygame.K_LSHIFT]:
            if not self.dash_key_pressed: 
                self.try_start_dash()
            self.dash_key_pressed = True
        else:
            self.dash_key_pressed = False

        if self.is_dashing:
            self.update_dash()

    def draw(self, surface):
        # Afterimages
        for afterimage in list(self.afterimages):
            alpha = afterimage.get_alpha()
            if alpha <= 0:
                try:
                    self.afterimages.remove(afterimage)
                except ValueError:
                    pass
                continue
            surf = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
            surf.fill((255, 255, 255, alpha))
            pos = (afterimage.pos[0] - PLAYER_SIZE / 2, afterimage.pos[1] - PLAYER_SIZE / 2)
            surface.blit(surf, pos)

        # Player
        color = (255, 255, 255)
        if self.hit_flash:
            color = (255, 0, 0)
            if pygame.time.get_ticks() - self.hit_time > HIT_FLASH_DURATION:
                self.hit_flash = False
        pygame.draw.rect(surface, color, self.rect)


class Level2:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((V_WIDTH, V_HEIGHT))
        pygame.display.set_caption("Level 2 - Neon Arena")
        self.clock = pygame.time.Clock()
        self.running = True

        self.bounds_rect = pygame.Rect(0, 0, V_WIDTH, V_HEIGHT)
        self.player = Player(V_WIDTH//2, V_HEIGHT//2)

        # Neon background
        self.color_index = random.randrange(len(NEON_COLORS))
        self.border_color, self.floor_color = NEON_COLORS[self.color_index]
        self.last_color_change = pygame.time.get_ticks()
        self.pulse_start = None
        self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.player.update(keys, self.bounds_rect)

        # Neon background pulse
        now = pygame.time.get_ticks()
        if now - self.last_color_change > 3000:
            indices = [i for i in range(len(NEON_COLORS)) if i != self.color_index]
            self.color_index = random.choice(indices)
            self.border_color, self.floor_color = NEON_COLORS[self.color_index]
            self.pulse_start = now
            self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)
            self.last_color_change = now

    def draw(self):
        # background
        self.screen.fill(self.floor_color)
        pygame.draw.rect(self.screen, self.border_color, (0,0,V_WIDTH,V_HEIGHT), BORDER_THICKNESS)

        # pulse overlay
        if self.pulse_start:
            elapsed = pygame.time.get_ticks() - self.pulse_start
            if elapsed < PULSE_DURATION:
                alpha = int(PULSE_ALPHA * (1 - elapsed / PULSE_DURATION))
                overlay = pygame.Surface((V_WIDTH, V_HEIGHT), pygame.SRCALPHA)
                overlay.fill((*self.pulse_color, alpha))
                self.screen.blit(overlay, (0,0))
            else:
                self.pulse_start = None

        # health bar
        hp_percent = max(0.0, min(1.0, self.player.health / PLAYER_MAX_HEALTH))
        bar_rect = pygame.Rect(10, 10, int(200 * hp_percent), 20)
        bar_color = (int(255 * (1 - hp_percent)), int(255 * hp_percent), 0)
        pygame.draw.rect(self.screen, bar_color, bar_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), (10, 10, 200, 20), 2)

        # player
        self.player.draw(self.screen)

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Level2().run()
