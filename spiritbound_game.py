import pygame
import sys
import random
import math

# --- Constants ---
V_WIDTH, V_HEIGHT = 640, 480  # virtual game resolution
PLAYER_SIZE = 32
FPS = 60
DASH_SPEED = 30
DASH_FRAMES = 3
DASH_COOLDOWN = 400
AFTERIMAGE_LIFETIME = 250
BORDER_THICKNESS = 5  # thickness of neon boundary

# --- Pulse effect ---
PULSE_DURATION = 500  # milliseconds
PULSE_ALPHA = 100     # max alpha of overlay

# --- Hit effect ---
HIT_FLASH_DURATION = 150  # milliseconds
HIT_SHAKE_INTENSITY = 5   # pixels

# --- Neon color palettes ---
NEON_COLORS = [
    ((0, 255, 180), (0, 100, 70)),
    ((0, 200, 255), (0, 80, 100)),
    ((140, 0, 255), (80, 0, 120)),
    ((0, 255, 120), (0, 100, 50)),
]

# -------------------------- CLASSES --------------------------

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
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 3

        # Dash
        self.dash_cooldown = DASH_COOLDOWN
        self.last_dash = -DASH_COOLDOWN
        self.dashing = False
        self.dash_dir = pygame.Vector2(0, 0)
        self.dash_progress = 0
        self.afterimages = []

        self.facing = pygame.Vector2(0, 1)
        self.dash_key_pressed = False

        # Hit state
        self.hit_flash = False
        self.hit_time = 0

    def update(self, keys, bounds_rect):
        dx, dy = 0, 0
        now = pygame.time.get_ticks()

        # DASH
        if keys[pygame.K_LSHIFT]:
            if not self.dash_key_pressed and now - self.last_dash >= self.dash_cooldown:
                self.start_dash()
            self.dash_key_pressed = True
        else:
            self.dash_key_pressed = False

        # MOVEMENT
        if not self.dashing:
            if keys[pygame.K_UP]:
                dy = -self.speed
                self.facing = pygame.Vector2(0, -1)
            elif keys[pygame.K_DOWN]:
                dy = self.speed
                self.facing = pygame.Vector2(0, 1)
            elif keys[pygame.K_LEFT]:
                dx = -self.speed
                self.facing = pygame.Vector2(-1, 0)
            elif keys[pygame.K_RIGHT]:
                dx = self.speed
                self.facing = pygame.Vector2(1, 0)

            if dx != 0 and dy != 0:
                dy = 0

            self.rect.x += dx
            self.rect.y += dy

            # Clamp inside bounds
            self.rect.left = max(self.rect.left, bounds_rect.left + BORDER_THICKNESS)
            self.rect.right = min(self.rect.right, bounds_rect.right - BORDER_THICKNESS)
            self.rect.top = max(self.rect.top, bounds_rect.top + BORDER_THICKNESS)
            self.rect.bottom = min(self.rect.bottom, bounds_rect.bottom - BORDER_THICKNESS)

        # DASH
        if self.dashing:
            self.rect.x += self.dash_dir.x * DASH_SPEED
            self.rect.y += self.dash_dir.y * DASH_SPEED

            # Clamp inside bounds
            self.rect.left = max(self.rect.left, bounds_rect.left + BORDER_THICKNESS)
            self.rect.right = min(self.rect.right, bounds_rect.right - BORDER_THICKNESS)
            self.rect.top = max(self.rect.top, bounds_rect.top + BORDER_THICKNESS)
            self.rect.bottom = min(self.rect.bottom, bounds_rect.bottom - BORDER_THICKNESS)

            self.dash_progress += 1
            if self.dash_progress in (1, 2, 3):
                self.afterimages.append(AfterImage(self.rect.center, self.dash_progress, DASH_FRAMES))
            if self.dash_progress >= DASH_FRAMES:
                self.dashing = False
                self.dash_progress = 0
                self.last_dash = now

    def start_dash(self):
        self.dashing = True
        self.dash_dir = self.facing.copy()
        self.dash_progress = 0

class SwordTrail:
    def __init__(self, start_pos, end_pos, lifetime=150):
        self.start = start_pos
        self.end = end_pos
        self.created_at = pygame.time.get_ticks()
        self.lifetime = lifetime

    def get_alpha(self):
        elapsed = pygame.time.get_ticks() - self.created_at
        if elapsed > self.lifetime:
            return 0
        return int(255 * (1 - elapsed / self.lifetime))

class Knight(pygame.sprite.Sprite):
    def __init__(self, x, y, target, bounds_rect, all_knights):
        super().__init__()
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill((200, 50, 50))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 2.0
        self.target = target
        self.bounds_rect = bounds_rect
        self.all_knights = all_knights

        # Sword
        self.sword_length = 80
        self.swinging = False
        self.swing_cooldown = 1000
        self.last_swing = -1000
        self.swing_duration = 150
        self.swing_start_time = None
        self.sword_trails = []

        self.attack_range = 60

    def update(self):
        now = pygame.time.get_ticks()
        dx = self.target.rect.centerx - self.rect.centerx
        dy = self.target.rect.centery - self.rect.centery
        distance = math.hypot(dx, dy)

        if self.swinging:
            elapsed = now - self.swing_start_time
            if elapsed > self.swing_duration:
                self.swinging = False
            else:
                t = elapsed / self.swing_duration
                angle_offset = math.radians(90) * (t - 0.5)
                base_angle = math.atan2(dy, dx)
                sword_angle = base_angle + angle_offset
                start_pos = self.rect.center
                end_pos = (start_pos[0] + math.cos(sword_angle) * self.sword_length,
                           start_pos[1] + math.sin(sword_angle) * self.sword_length)
                self.sword_trails.append(SwordTrail(start_pos, end_pos))
                player_rect = self.target.rect
                line_rect = pygame.Rect(min(start_pos[0], end_pos[0]),
                                        min(start_pos[1], end_pos[1]),
                                        abs(end_pos[0]-start_pos[0])+1,
                                        abs(end_pos[1]-start_pos[1])+1)
                if line_rect.colliderect(player_rect):
                    self.target.hit_flash = True
                    self.target.hit_time = now
        else:
            if distance <= self.attack_range and now - self.last_swing >= self.swing_cooldown:
                self.swinging = True
                self.swing_start_time = now
                self.last_swing = now
            elif distance > self.attack_range and distance != 0:
                # Move toward player
                move_x = dx / distance * self.speed
                move_y = dy / distance * self.speed

                # Collision avoidance with other knights
                for other in self.all_knights:
                    if other == self:
                        continue
                    if self.rect.colliderect(other.rect):
                        # Determine which knight is further from player
                        my_dist = math.hypot(self.target.rect.centerx - self.rect.centerx,
                                             self.target.rect.centery - self.rect.centery)
                        other_dist = math.hypot(self.target.rect.centerx - other.rect.centerx,
                                                self.target.rect.centery - other.rect.centery)
                        if my_dist > other_dist:
                            # Move slightly perpendicular to avoid overlap
                            perp_angle = math.atan2(dy, dx) + math.pi/2
                            move_x += math.cos(perp_angle) * self.speed * 0.5
                            move_y += math.sin(perp_angle) * self.speed * 0.5
                        else:
                            move_x = move_y = 0  # Stop to let closer knight pass

                self.rect.x += move_x
                self.rect.y += move_y
                self.rect.clamp_ip(self.bounds_rect)

    def draw(self, surface, scale_x=1, scale_y=1):
        scaled_rect = pygame.Rect(
            self.rect.x * scale_x, self.rect.y * scale_y,
            PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y
        )
        pygame.draw.rect(surface, (200, 50, 50), scaled_rect)

        if self.swinging:
            elapsed = pygame.time.get_ticks() - self.swing_start_time
            t = elapsed / self.swing_duration
            dx = self.target.rect.centerx - self.rect.centerx
            dy = self.target.rect.centery - self.rect.centery
            base_angle = math.atan2(dy, dx)
            angle_offset = math.radians(90) * (t - 0.5)
            sword_angle = base_angle + angle_offset
            start = (self.rect.centerx * scale_x, self.rect.centery * scale_y)
            end = (start[0] + math.cos(sword_angle) * self.sword_length * scale_x,
                   start[1] + math.sin(sword_angle) * self.sword_length * scale_y)
            pygame.draw.line(surface, (255, 255, 255), start, end, 4)

        for trail in self.sword_trails[:]:
            alpha = trail.get_alpha()
            if alpha <= 0:
                self.sword_trails.remove(trail)
                continue
            sx = trail.start[0] * scale_x
            sy = trail.start[1] * scale_y
            ex = trail.end[0] * scale_x
            ey = trail.end[1] * scale_y
            pygame.draw.line(surface, (255, 255, 255, alpha), (sx, sy), (ex, ey), 4)


# -------------------------- GAME --------------------------

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((V_WIDTH, V_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Spiritbound - Neon Arena")
        self.clock = pygame.time.Clock()
        self.running = True

        self.virtual_width = V_WIDTH
        self.virtual_height = V_HEIGHT
        self.window_width, self.window_height = V_WIDTH, V_HEIGHT

        self.bounds_rect = pygame.Rect(0, 0, self.virtual_width, self.virtual_height)
        self.player = Player(self.virtual_width // 2, self.virtual_height // 2)
        self.all_sprites = pygame.sprite.Group(self.player)

        self.knights = pygame.sprite.Group()
        # Pass reference to all_knights to each Knight
        for pos in [(100, 100), (500, 300), (300, 200)]:
            knight = Knight(pos[0], pos[1], self.player, self.bounds_rect, self.knights)
            self.knights.add(knight)

        self.color_index = random.randrange(len(NEON_COLORS))
        self.border_color, self.floor_color = NEON_COLORS[self.color_index]

        self.last_color_change = pygame.time.get_ticks()
        self.color_interval = 3000

        # Pulse effect
        self.pulse_start = None
        self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)

    def change_color(self):
        possible_indices = [i for i in range(len(NEON_COLORS)) if i != self.color_index]
        new_index = random.choice(possible_indices)
        self.color_index = new_index
        self.border_color, self.floor_color = NEON_COLORS[new_index]
        self.pulse_start = pygame.time.get_ticks()
        self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.window_width, self.window_height = event.w, event.h
                self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.player.update(keys, self.bounds_rect)
        for knight in self.knights:
            knight.update()

        now = pygame.time.get_ticks()
        if now - self.last_color_change > self.color_interval:
            self.change_color()
            self.last_color_change = now

    def draw(self):
        scale_x = self.window_width / self.virtual_width
        scale_y = self.window_height / self.virtual_height

        # Shake offset if player hit
        offset_x = offset_y = 0
        if self.player.hit_flash:
            elapsed = pygame.time.get_ticks() - self.player.hit_time
            if elapsed < HIT_FLASH_DURATION:
                offset_x = random.randint(-HIT_SHAKE_INTENSITY, HIT_SHAKE_INTENSITY)
                offset_y = random.randint(-HIT_SHAKE_INTENSITY, HIT_SHAKE_INTENSITY)
            else:
                self.player.hit_flash = False

        self.screen.fill(self.floor_color)

        # Draw boundary
        pygame.draw.rect(self.screen, self.border_color,
                         pygame.Rect(offset_x, offset_y, self.window_width, self.window_height), BORDER_THICKNESS)

        # Draw afterimages
        for afterimage in self.player.afterimages[:]:
            alpha = afterimage.get_alpha()
            if alpha <= 0:
                self.player.afterimages.remove(afterimage)
                continue
            surf = pygame.Surface((PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y), pygame.SRCALPHA)
            surf.fill((255, 255, 255, alpha))
            pos = (afterimage.pos[0] * scale_x + offset_x, afterimage.pos[1] * scale_y + offset_y)
            self.screen.blit(surf, (pos[0] - PLAYER_SIZE * scale_x / 2, pos[1] - PLAYER_SIZE * scale_y / 2))

        # Draw player
        scaled_rect = pygame.Rect(
            self.player.rect.x * scale_x + offset_x,
            self.player.rect.y * scale_y + offset_y,
            PLAYER_SIZE * scale_x,
            PLAYER_SIZE * scale_y
        )
        pygame.draw.rect(self.screen, (255, 255, 255), scaled_rect)

        # Draw knights
        for knight in self.knights:
            knight.draw(self.screen, scale_x, scale_y)

        # Draw pulse overlay if active
        if self.pulse_start:
            elapsed = pygame.time.get_ticks() - self.pulse_start
            if elapsed < PULSE_DURATION:
                alpha = int(PULSE_ALPHA * (1 - elapsed / PULSE_DURATION))
                overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                overlay.fill((*self.pulse_color, alpha))
                self.screen.blit(overlay, (0, 0))
            else:
                self.pulse_start = None

        # Draw red flash overlay if hit
        if self.player.hit_flash:
            elapsed = pygame.time.get_ticks() - self.player.hit_time
            if elapsed < HIT_FLASH_DURATION:
                alpha = int(150 * (1 - elapsed / HIT_FLASH_DURATION))
                overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                overlay.fill((255, 0, 0, alpha))
                self.screen.blit(overlay, (0, 0))

        pygame.display.flip()

# -------------------------- RUN --------------------------

if __name__ == "__main__":
    Game().run()
