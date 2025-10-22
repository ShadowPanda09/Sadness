import pygame
import sys
import random
import math

# --- Constants ---
V_WIDTH, V_HEIGHT = 640, 480
PLAYER_SIZE = 32
FPS = 60
BORDER_THICKNESS = 5

# --- Dash Settings ---
DASH_SPEED = 400
DASH_TIME = 150  # ms
DASH_COOLDOWN = 1000  # ms

# Sword / combat timings (ms)
PLAYER_SWING_DURATION = 350
PLAYER_SWING_COOLDOWN = 900
PLAYER_SWORD_LENGTH = 60
PLAYER_SWORD_HIT_RADIUS = 28

ENEMY_SWING_DURATION = 350
ENEMY_SWING_COOLDOWN = 1000
ENEMY_SWORD_LENGTH = 60
ENEMY_SWORD_HIT_RADIUS = 28

# Trails
TRAIL_LIFETIME = 220
TRAIL_MAX_POINTS = 16

# Effects
PULSE_DURATION = 500
PULSE_ALPHA = 100
HIT_FLASH_DURATION = 150

# Color palette
NEON_COLORS = [
    ((0, 255, 180), (0, 100, 70)),
    ((0, 200, 255), (0, 80, 100)),
    ((140, 0, 255), (80, 0, 120)),
    ((0, 255, 120), (0, 100, 50)),
]


# -------------------- Helper Classes --------------------

class SwordTrail:
    def __init__(self, start, end, lifetime=TRAIL_LIFETIME):
        self.start = start
        self.end = end
        self.created = pygame.time.get_ticks()
        self.lifetime = lifetime

    def alpha(self):
        elapsed = pygame.time.get_ticks() - self.created
        if elapsed >= self.lifetime:
            return 0
        return int(255 * (1 - elapsed / self.lifetime))


# -------------------- Player --------------------

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(0, 0, PLAYER_SIZE, PLAYER_SIZE)
        self.rect.center = (x, y)
        self.speed = 2.8

        # Sword state
        self.swinging = False
        self.swing_start = 0
        self.swing_duration = PLAYER_SWING_DURATION
        self.swing_cooldown = PLAYER_SWING_COOLDOWN
        self.last_swing = -PLAYER_SWING_COOLDOWN
        self.locked_angle = 0.0
        self.sword_length = PLAYER_SWORD_LENGTH
        self.trails = []

        # Dash
        self.dashing = False
        self.dash_timer = DASH_COOLDOWN
        self.dash_start = 0
        self.dash_dir = pygame.Vector2(0, 0)
        self.invincible = False
        self.last_move_dir = pygame.Vector2(1, 0)

        # Hit state
        self.hit_flash = False
        self.hit_time = 0

    def start_dash(self):
        now = pygame.time.get_ticks()
        if not self.dashing and (now - self.dash_timer) >= DASH_COOLDOWN and self.last_move_dir.length_squared() > 0:
            self.dashing = True
            self.dash_start = now
            self.dash_timer = now
            self.dash_dir = self.last_move_dir.normalize()
            self.invincible = True
            self.swinging = False  # cancel sword swing mid-dash

    def update_dash(self, dt):
        if self.dashing:
            now = pygame.time.get_ticks()
            elapsed = now - self.dash_start
            if elapsed < DASH_TIME:
                move = self.dash_dir * (DASH_SPEED * (dt / 1000))
                self.rect.x += int(move.x)
                self.rect.y += int(move.y)
            else:
                self.dashing = False
                self.invincible = False

    def start_swing(self, aim_angle):
        now = pygame.time.get_ticks()
        if now - self.last_swing >= self.swing_cooldown and not self.swinging:
            self.swinging = True
            self.swing_start = now
            self.last_swing = now
            self.locked_angle = aim_angle
            tip = (self.rect.centerx + math.cos(self.locked_angle) * self.sword_length,
                   self.rect.centery + math.sin(self.locked_angle) * self.sword_length)
            self.trails.append(SwordTrail(self.rect.center, tip))

    def update(self, keys, mouse_pos, mouse_pressed, bounds_rect, enemies_group, dt):
        now = pygame.time.get_ticks()

        # Movement
        move_dir = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            move_dir.y -= 1
        if keys[pygame.K_s]:
            move_dir.y += 1
        if keys[pygame.K_a]:
            move_dir.x -= 1
        if keys[pygame.K_d]:
            move_dir.x += 1

        if move_dir.length_squared() > 0:
            move_dir = move_dir.normalize()
            self.last_move_dir = move_dir

        if not self.dashing:
            self.rect.x += int(move_dir.x * self.speed)
            self.rect.y += int(move_dir.y * self.speed)

        # Dash (Left Shift)
        if keys[pygame.K_LSHIFT]:
            self.start_dash()
        self.update_dash(dt)

        # Bounds
        self.rect.clamp_ip(bounds_rect)

        # Aiming
        mx, my = mouse_pos
        aim_angle = math.atan2(my - self.rect.centery, mx - self.rect.centerx)

        # Attack
        if mouse_pressed[0]:
            self.start_swing(aim_angle)

        # Sword swing logic
        if self.swinging:
            elapsed = now - self.swing_start
            t = elapsed / self.swing_duration
            if elapsed >= self.swing_duration:
                self.swinging = False
            else:
                arc = math.radians(100)
                offset = -arc / 2 + arc * t
                sword_angle = self.locked_angle + offset
                start = (self.rect.centerx, self.rect.centery)
                tip = (start[0] + math.cos(sword_angle) * self.sword_length,
                       start[1] + math.sin(sword_angle) * self.sword_length)
                self.trails.append(SwordTrail(start, tip))
                if len(self.trails) > TRAIL_MAX_POINTS:
                    self.trails.pop(0)
                for enemy in list(enemies_group):
                    ex, ey = enemy.rect.center
                    if math.hypot(ex - tip[0], ey - tip[1]) <= PLAYER_SWORD_HIT_RADIUS:
                        enemy.kill()

        # Trail cleanup
        self.trails = [tr for tr in self.trails if tr.alpha() > 0]

    def draw(self, surface):
        pygame.draw.rect(surface, (255, 255, 255), self.rect)

        # Sword swing
        if self.swinging:
            elapsed = pygame.time.get_ticks() - self.swing_start
            t = elapsed / self.swing_duration
            arc = math.radians(100)
            offset = -arc / 2 + arc * t
            sword_angle = self.locked_angle + offset
            start = (self.rect.centerx, self.rect.centery)
            tip = (start[0] + math.cos(sword_angle) * self.sword_length,
                   start[1] + math.sin(sword_angle) * self.sword_length)
            pygame.draw.line(surface, (255, 255, 255), start, tip, 4)

        # Sword trails
        for tr in self.trails:
            a = tr.alpha()
            if a <= 0:
                continue
            sx, sy = tr.start
            ex, ey = tr.end
            minx, miny = int(min(sx, ex)), int(min(sy, ey))
            w, h = max(2, int(abs(ex - sx))), max(2, int(abs(ey - sy)))
            surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
            pygame.draw.line(surf, (255, 255, 255, a),
                             (sx - minx + 2, sy - miny + 2),
                             (ex - minx + 2, ey - miny + 2), 3)
            surface.blit(surf, (minx - 2, miny - 2))


# -------------------- Enemy --------------------

class Knight(pygame.sprite.Sprite):
    def __init__(self, x, y, target, bounds_rect, all_knights_group):
        super().__init__()
        self.rect = pygame.Rect(0, 0, PLAYER_SIZE, PLAYER_SIZE)
        self.rect.center = (x, y)
        self.color = (200, 50, 50)
        self.speed = 1.8
        self.target = target
        self.bounds_rect = bounds_rect
        self.all_knights = all_knights_group
        self.swinging = False
        self.swing_start = 0
        self.swing_duration = ENEMY_SWING_DURATION
        self.swing_cooldown = ENEMY_SWING_COOLDOWN
        self.last_swing = -ENEMY_SWING_COOLDOWN
        self.locked_angle = 0.0
        self.sword_length = ENEMY_SWORD_LENGTH
        self.trails = []
        self.attack_range = 70

    def start_swing(self, angle):
        now = pygame.time.get_ticks()
        if now - self.last_swing >= self.swing_cooldown and not self.swinging:
            self.swinging = True
            self.swing_start = now
            self.last_swing = now
            self.locked_angle = angle

    def update(self):
        now = pygame.time.get_ticks()
        dx = self.target.rect.centerx - self.rect.centerx
        dy = self.target.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy) or 0.001

        if self.swinging:
            elapsed = now - self.swing_start
            if elapsed >= self.swing_duration:
                self.swinging = False
            else:
                arc = math.radians(100)
                t = elapsed / self.swing_duration
                sword_angle = self.locked_angle - arc / 2 + arc * t
                start = self.rect.center
                tip = (start[0] + math.cos(sword_angle) * self.sword_length,
                       start[1] + math.sin(sword_angle) * self.sword_length)
                self.trails.append(SwordTrail(start, tip))
                for tr in self.trails[:]:
                    if tr.alpha() <= 0:
                        self.trails.remove(tr)
                px, py = self.target.rect.center
                if math.hypot(px - tip[0], py - tip[1]) <= ENEMY_SWORD_HIT_RADIUS:
                    self.target.hit_flash = True
                    self.target.hit_time = now
        else:
            if dist <= self.attack_range:
                self.start_swing(math.atan2(dy, dx))
            else:
                move_x = dx / dist * self.speed
                move_y = dy / dist * self.speed
                self.rect.x += int(move_x)
                self.rect.y += int(move_y)
                self.rect.clamp_ip(self.bounds_rect)

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        for tr in self.trails:
            a = tr.alpha()
            if a > 0:
                sx, sy = tr.start
                ex, ey = tr.end
                pygame.draw.line(surface, (255, 255, 255, a), (sx, sy), (ex, ey), 3)


# -------------------- GAME --------------------

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((V_WIDTH, V_HEIGHT))
        pygame.display.set_caption("Spiritbound - Arena")
        self.clock = pygame.time.Clock()
        self.bounds_rect = pygame.Rect(0, 0, V_WIDTH, V_HEIGHT)

        self.player = Player(V_WIDTH // 2, V_HEIGHT // 2)
        self.knights = pygame.sprite.Group()
        self.spawn_knights()

        self.border_color, self.floor_color = random.choice(NEON_COLORS)
        self.pulse_start = None
        self.last_respawn = 0
        self.last_color_change = pygame.time.get_ticks()

    def spawn_knights(self):
        k1 = Knight(100, 100, self.player, self.bounds_rect, self.knights)
        k2 = Knight(520, 340, self.player, self.bounds_rect, self.knights)
        self.knights.add(k1, k2)

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

    def update(self, dt):
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()

        self.player.update(keys, mouse_pos, mouse_pressed, self.bounds_rect, self.knights, dt)

        for k in list(self.knights):
            k.update()
            if not k.alive():
                self.knights.remove(k)

        # Respawn after all dead
        if len(self.knights) == 0 and pygame.time.get_ticks() - self.last_respawn > 2000:
            self.last_respawn = pygame.time.get_ticks()
            self.spawn_knights()

        # Color change every 3 seconds
        now = pygame.time.get_ticks()
        if now - self.last_color_change > 3000:
            self.last_color_change = now
            self.border_color, self.floor_color = random.choice(NEON_COLORS)
            self.pulse_start = now

    def draw(self):
        self.screen.fill(self.floor_color)
        pygame.draw.rect(self.screen, self.border_color,
                         pygame.Rect(0, 0, V_WIDTH, V_HEIGHT), BORDER_THICKNESS)

        for k in self.knights:
            k.draw(self.screen)
        self.player.draw(self.screen)

        # Pulse effect
        if self.pulse_start:
            elapsed = pygame.time.get_ticks() - self.pulse_start
            if elapsed < PULSE_DURATION:
                alpha = int(PULSE_ALPHA * (1 - elapsed / PULSE_DURATION))
                overlay = pygame.Surface((V_WIDTH, V_HEIGHT), pygame.SRCALPHA)
                overlay.fill((*self.border_color, alpha))
                self.screen.blit(overlay, (0, 0))
            else:
                self.pulse_start = None

        # Hit flash
        if self.player.hit_flash:
            elapsed = pygame.time.get_ticks() - self.player.hit_time
            if elapsed < HIT_FLASH_DURATION:
                alpha = int(140 * (1 - elapsed / HIT_FLASH_DURATION))
                overlay = pygame.Surface((V_WIDTH, V_HEIGHT), pygame.SRCALPHA)
                overlay.fill((255, 0, 0, alpha))
                self.screen.blit(overlay, (0, 0))
            else:
                self.player.hit_flash = False

        pygame.display.flip()


# -------------------- Run --------------------

if __name__ == "__main__":
    Game().run()
