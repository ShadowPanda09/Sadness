import pygame
import sys
import random
import math
import os

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

# Sword/combat
PLAYER_SWING_DURATION_MS = 150
PLAYER_SWING_COOLDOWN_MS = 300
PLAYER_SWORD_LENGTH = 60
PLAYER_SWORD_HIT_RADIUS = 28

# Trail
TRAIL_LIFETIME_MS = 220
TRAIL_MAX_POINTS = 16

# Effects
PULSE_DURATION = 500
PULSE_ALPHA = 100
HIT_FLASH_DURATION = 150
HIT_SHAKE_INTENSITY = 5
DEATH_FADE_DURATION = 1000

# Colors
NEON_COLORS = [
    ((0, 255, 180), (0, 100, 70)),
    ((0, 200, 255), (0, 80, 100)),
    ((140, 0, 255), (80, 0, 120)),
    ((0, 255, 120), (0, 100, 50)),
]

# Health / damage
PLAYER_MAX_HEALTH = 100
KNIGHT_DAMAGE = 15
SWORD_DAMAGE = 40

# Enemy attack visuals/settings
ENEMY_ATTACK_LENGTH = 80
ENEMY_ATTACK_ARC = math.radians(90)
ENEMY_ATTACK_DURATION = 300
ENEMY_ATTACK_COOLDOWN = 1000
ENEMY_BASE_SPEED = 3.75

# -------------------------- Utility classes --------------------------

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


class SwordTrail:
    def __init__(self, start_pos, end_pos, lifetime_ms=TRAIL_LIFETIME_MS):
        self.start = start_pos
        self.end = end_pos
        self.created_at = pygame.time.get_ticks()
        self.lifetime = lifetime_ms

    def get_alpha(self):
        elapsed = pygame.time.get_ticks() - self.created_at
        if elapsed > self.lifetime:
            return 0
        return int(255 * (1 - elapsed / self.lifetime))


# -------------------------- Player --------------------------

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.health = PLAYER_MAX_HEALTH
        self.dead = False
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(self.rect.center)

        # movement
        self.speed = 3
        self.facing = pygame.Vector2(0, 1)

        # dash
        self.dash_cooldown = DASH_COOLDOWN
        self.last_dash = -DASH_COOLDOWN
        self.is_dashing = False
        self.dash_dir = pygame.Vector2(0, -1)
        self.dash_start_time = 0
        self.dash_progress = 0
        self.afterimages = []
        self._next_afterimage_at = 0
        self.dash_key_pressed = False

        # sword
        self.swinging = False
        self.swing_start_time = 0
        self.swing_duration = PLAYER_SWING_DURATION_MS
        self.swing_cooldown = PLAYER_SWING_COOLDOWN_MS
        self.last_swing = -PLAYER_SWING_COOLDOWN_MS
        self.locked_angle = 0.0
        self.sword_length = PLAYER_SWORD_LENGTH
        self.sword_trails = []

        # hit / invulnerability
        self.hit_flash = False
        self.hit_time = 0
        self.invincible = False
        self.invincibility_timer = 0  # milliseconds

        # misc
        self.death_time = None

    def try_start_dash(self):
        now = pygame.time.get_ticks()
        if self.dead or self.is_dashing:
            return
        if (now - self.last_dash) < self.dash_cooldown:
            return
        if self.facing.length_squared() == 0:
            self.dash_dir = pygame.Vector2(0, -1)
        else:
            self.dash_dir = self.facing.normalize()
        self.is_dashing = True
        self.dash_start_time = now
        self.last_dash = now
        self._next_afterimage_at = now
        self.afterimages.clear()
        self.afterimages.append(AfterImage(self.pos, 1, DASH_FRAMES))
        self.swinging = False

    def try_start_swing(self, aim_angle):
        now = pygame.time.get_ticks()
        if self.dead or self.is_dashing:
            return
        if (now - self.last_swing) >= self.swing_cooldown and not self.swinging:
            self.swinging = True
            self.swing_start_time = now
            self.last_swing = now
            self.locked_angle = aim_angle
            tip = (self.pos.x + math.cos(self.locked_angle) * self.sword_length,
                   self.pos.y + math.sin(self.locked_angle) * self.sword_length)
            self.sword_trails.append(SwordTrail((self.pos.x, self.pos.y), tip))

    def take_damage(self, amount):
        """Centralized damage handling for the player."""
        if self.dead:
            return
        if self.invincible:
            return
        now = pygame.time.get_ticks()
        self.hit_flash = True
        self.hit_time = now
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.dead = True
            self.death_time = now

    def update_dash(self, dt_ms):
        if not self.is_dashing:
            return
        now = pygame.time.get_ticks()
        # move by dash speed per frame (keeps behaviour consistent)
        self.pos += self.dash_dir * DASH_SPEED
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        if now >= self._next_afterimage_at and len(self.afterimages) < DASH_FRAMES:
            self.afterimages.append(AfterImage(self.pos, len(self.afterimages) + 1, DASH_FRAMES))
            self._next_afterimage_at = now + (DASH_COOLDOWN // max(1, DASH_FRAMES))
        self.dash_progress += 1
        if self.dash_progress >= DASH_FRAMES:
            self.is_dashing = False
            self.dash_progress = 0
            self.afterimages.clear()

    def update(self, keys, bounds_rect, dt_ms):
        now = pygame.time.get_ticks()

        # dash input (LSHIFT)
        if keys[pygame.K_LSHIFT]:
            if not self.dash_key_pressed:
                self.try_start_dash()
            self.dash_key_pressed = True
        else:
            self.dash_key_pressed = False

        # movement when not dashing or swinging
        if not self.is_dashing and not self.swinging:
            move_vec = pygame.Vector2(0, 0)
            if keys[pygame.K_w]:
                move_vec.y -= 1
            if keys[pygame.K_s]:
                move_vec.y += 1
            if keys[pygame.K_a]:
                move_vec.x -= 1
            if keys[pygame.K_d]:
                move_vec.x += 1
            if move_vec.length_squared() > 0:
                if abs(move_vec.x) > 0 and abs(move_vec.y) > 0:
                    move_vec.y = 0
                self.facing = move_vec.normalize()
                self.pos += move_vec.normalize() * self.speed
                self.rect.center = (int(self.pos.x), int(self.pos.y))
                self.rect.clamp_ip(bounds_rect)
                self.pos = pygame.Vector2(self.rect.center)

        # dash update (also possible to call update_dash separately)
        if self.is_dashing:
            self.pos += self.dash_dir * DASH_SPEED
            self.rect.center = (int(self.pos.x), int(self.pos.y))
            self.rect.clamp_ip(bounds_rect)
            if now >= self._next_afterimage_at and len(self.afterimages) < DASH_FRAMES:
                self.afterimages.append(AfterImage(self.pos, len(self.afterimages) + 1, DASH_FRAMES))
                self._next_afterimage_at = now + max(1, int(self.swing_duration / max(1, DASH_FRAMES)))
            self.dash_progress += 1
            if self.dash_progress >= DASH_FRAMES:
                self.is_dashing = False
                self.dash_progress = 0
                self.afterimages.clear()

        # swing update - generate trails while swinging
        if self.swinging:
            elapsed = now - self.swing_start_time
            if elapsed >= self.swing_duration:
                self.swinging = False
            else:
                t = elapsed / self.swing_duration
                arc = math.radians(100)
                offset = -arc / 2 + arc * t
                sword_angle = self.locked_angle + offset
                start = (self.pos.x, self.pos.y)
                tip = (start[0] + math.cos(sword_angle) * self.sword_length,
                       start[1] + math.sin(sword_angle) * self.sword_length)
                self.sword_trails.append(SwordTrail(start, tip))
                if len(self.sword_trails) > TRAIL_MAX_POINTS:
                    self.sword_trails.pop(0)

        # invincibility timer - dt_ms is milliseconds
        if self.invincible:
            self.invincibility_timer -= dt_ms
            if self.invincibility_timer <= 0:
                self.invincible = False
                self.invincibility_timer = 0

    def draw(self, surface, scale_x=1, scale_y=1):
        # afterimages
        for afterimage in self.afterimages[:]:
            alpha = afterimage.get_alpha()
            if alpha <= 0:
                try:
                    self.afterimages.remove(afterimage)
                except ValueError:
                    pass
                continue
            surf = pygame.Surface((PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y), pygame.SRCALPHA)
            surf.fill((255, 255, 255, alpha))
            pos = (afterimage.pos[0] * scale_x, afterimage.pos[1] * scale_y)
            surface.blit(surf, (pos[0] - PLAYER_SIZE * scale_x / 2, pos[1] - PLAYER_SIZE * scale_y / 2))

        # player body (you can add a visual when invincible if desired)
        scaled_rect = pygame.Rect(self.rect.x * scale_x, self.rect.y * scale_y,
                                  PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y)
        pygame.draw.rect(surface, (255, 255, 255), scaled_rect)

        # draw current sword arc if swinging
        now = pygame.time.get_ticks()
        if self.swinging:
            elapsed = now - self.swing_start_time
            t = elapsed / self.swing_duration if self.swing_duration else 1.0
            arc = math.radians(100)
            offset = -arc / 2 + arc * t
            sword_angle = self.locked_angle + offset
            start = (self.rect.centerx * scale_x, self.rect.centery * scale_y)
            tip = (start[0] + math.cos(sword_angle) * self.sword_length * scale_x,
                   start[1] + math.sin(sword_angle) * self.sword_length * scale_y)
            pygame.draw.line(surface, (255, 255, 255), start, tip, 4)

        # sword trails
        for trail in list(self.sword_trails):
            alpha = trail.get_alpha()
            if alpha <= 0:
                try:
                    self.sword_trails.remove(trail)
                except ValueError:
                    pass
                continue
            sx, sy = trail.start
            ex, ey = trail.end
            sx *= scale_x; sy *= scale_y; ex *= scale_x; ey *= scale_y
            surf = pygame.Surface((abs(int(ex - sx)) + 6, abs(int(ey - sy)) + 6), pygame.SRCALPHA)
            pygame.draw.line(surf, (255, 255, 255, alpha),
                             ((0 if ex >= sx else abs(int(ex - sx))), (0 if ey >= sy else abs(int(ey - sy)))),
                             ((abs(int(ex - sx)) if ex >= sx else 0), (abs(int(ey - sy)) if ey >= sy else 0)), 3)
            min_x = int(min(sx, ex)) - 2
            min_y = int(min(sy, ey)) - 2
            surface.blit(surf, (min_x, min_y))


# -------------------------- Knight (enemy) --------------------------

class Knight(pygame.sprite.Sprite):
    def __init__(self, x, y, target, bounds_rect, all_knights):
        super().__init__()
        self.start_pos = pygame.Vector2(x, y)
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill((200, 50, 50))
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(self.rect.center)
        self.speed = ENEMY_BASE_SPEED
        self.target = target
        self.bounds_rect = bounds_rect
        self.all_knights = all_knights

        self.health = 60
        self.hit_flash = False
        self.hit_time = 0

        # attack state
        self.attack_range = 60
        self.last_attack = -1000
        self.attack_cooldown = ENEMY_ATTACK_COOLDOWN
        self.attacking = False
        self.attack_start_time = 0
        self.attack_duration = ENEMY_ATTACK_DURATION
        self.attack_angle = 0.0
        self.attack_arc = ENEMY_ATTACK_ARC
        self.attack_length = ENEMY_ATTACK_LENGTH
        self.attack_damage = KNIGHT_DAMAGE

        # NEW: damage cooldown so knight cannot hit repeatedly
        self.damage_cooldown_ms = 500  # e.g., 0.5s per hit
        self.last_damage_time = -self.damage_cooldown_ms

        self.sword_trails = []

    def update(self):
        if getattr(self, "alive", True) is False:
            return
        now = pygame.time.get_ticks()
        dx = self.target.rect.centerx - self.rect.centerx
        dy = self.target.rect.centery - self.rect.centery
        distance = math.hypot(dx, dy)

        if self.attacking:
            elapsed = now - self.attack_start_time
            if elapsed > self.attack_duration:
                self.attacking = False
            else:
                if distance <= self.attack_range:
                    player_angle = math.atan2(dy, dx)
                    angle_diff = abs((player_angle - self.attack_angle + math.pi) % (2 * math.pi) - math.pi)
                    if angle_diff <= self.attack_arc / 2:
                        # Only apply damage if damage cooldown has passed
                        if now - self.last_damage_time >= self.damage_cooldown_ms:
                            self.last_damage_time = now
                            self.target.take_damage(self.attack_damage)
                return

        # start attack if in range and cooldown elapsed
        if distance <= self.attack_range and (now - self.last_attack) >= self.attack_cooldown:
            self.attacking = True
            self.attack_start_time = now
            self.attack_angle = math.atan2(dy, dx)
            self.last_attack = now
            return

        # movement toward player with avoidance
        if distance > 0:
            to_player = pygame.Vector2(dx, dy).normalize()
        else:
            to_player = pygame.Vector2(0, 0)

        avoidance = pygame.Vector2(0, 0)
        for other in self.all_knights:
            if other is self:
                continue
            if not hasattr(other, "rect"):
                continue
            offset = pygame.Vector2(self.rect.center) - pygame.Vector2(other.rect.center)
            d = offset.length()
            if 0 < d < PLAYER_SIZE * 1.5:
                offset.normalize_ip()
                avoidance += offset * ((PLAYER_SIZE * 1.5 - d) / (PLAYER_SIZE * 1.5))

        move_dir = to_player + avoidance
        if move_dir.length() > 0:
            move_dir.normalize_ip()
            self.pos += move_dir * (self.speed * (1.0 / (FPS / 60)))
            self.rect.center = (int(self.pos.x), int(self.pos.y))
            self.rect.clamp_ip(self.bounds_rect)
            self.pos = pygame.Vector2(self.rect.center)

    def take_damage(self, amount):
        self.health -= amount
        self.hit_flash = True
        self.hit_time = pygame.time.get_ticks()

    def draw(self, surface, scale_x=1, scale_y=1):
        color = (255, 120, 120) if self.hit_flash else (200, 50, 50)
        scaled_rect = pygame.Rect(self.rect.x * scale_x, self.rect.y * scale_y,
                                  PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y)
        pygame.draw.rect(surface, color, scaled_rect)

        # attack visual arc
        if self.attacking:
            elapsed = pygame.time.get_ticks() - self.attack_start_time
            progress = elapsed / max(1, self.attack_duration)
            alpha = int(180 * (1 - progress))
            alpha = max(0, min(255, alpha))
            if alpha > 0:
                overlay = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
                steps = 12
                cx = self.rect.centerx * scale_x
                cy = self.rect.centery * scale_y
                for i in range(steps):
                    t = i / (steps - 1)
                    angle = self.attack_angle - self.attack_arc / 2 + t * self.attack_arc
                    end_x = cx + math.cos(angle) * self.attack_length * scale_x
                    end_y = cy + math.sin(angle) * self.attack_length * scale_y
                    pygame.draw.line(overlay, (255, 60, 60, alpha), (cx, cy), (end_x, end_y), 3)
                surface.blit(overlay, (0, 0))

        if self.hit_flash and (pygame.time.get_ticks() - self.hit_time) > HIT_FLASH_DURATION:
            self.hit_flash = False


# -------------------------- Game --------------------------

class Game:
    def __init__(self):
        # respawn counters
        self.respawn_count = 0
        self.knight_speed_scale = 1.0
        self.music_path = os.path.join(os.path.dirname(__file__), "assets", "menu title music.mp3")

        pygame.init()
        self.screen = pygame.display.set_mode((V_WIDTH, V_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Spiritbound - Neon Arena")
        self.clock = pygame.time.Clock()
        self.running = True

        self.virtual_width = V_WIDTH
        self.virtual_height = V_HEIGHT
        self.window_width, self.window_height = V_WIDTH, V_HEIGHT

        self.bounds_rect = pygame.Rect(0, 0, self.virtual_width, self.virtual_height)

        # player
        self.player = Player(self.virtual_width // 2, self.virtual_height // 2)

        # spawn positions and knights
        self.spawn_positions = [
            (40, 40),
            (self.virtual_width - 40, 40),
            (40, self.virtual_height - 40),
            (self.virtual_width - 40, self.virtual_height - 40)
        ]
        self.knights = []
        for pos in self.spawn_positions:
            k = Knight(pos[0], pos[1], self.player, self.bounds_rect, self.knights)
            self.knights.append(k)

        # color/pulse state
        self.color_index = random.randrange(len(NEON_COLORS))
        self.border_color, self.floor_color = NEON_COLORS[self.color_index]
        self.last_color_change = pygame.time.get_ticks()
        self.color_interval = 3000
        self.pulse_start = None
        self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)

        # death/menu state
        self.death_fade_start = None
        self.show_retry = False
        self.show_restart = False

    # ---------- events ----------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.VIDEORESIZE:
                self.window_width, self.window_height = event.w, event.h
                self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

            # if a menu shown, it takes precedence
            if self.show_retry or self.show_restart:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        if self.show_retry:
                            self.respawn_player()
                            self.show_retry = False
                        elif self.show_restart:
                            self.restart_game()
                            self.show_restart = False
                        self.death_fade_start = None
                    elif event.key == pygame.K_m:
                        try:
                            import spiritbound_title
                            pygame.mixer.stop()
                            pygame.display.quit()
                            spiritbound_title.main_menu()
                        except Exception:
                            self.running = False
                            pygame.quit()
                            sys.exit()
                        return
                continue

            # normal inputs
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LSHIFT:
                    self.player.try_start_dash()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    aim_angle = math.atan2(my - self.player.rect.centery, mx - self.player.rect.centerx)
                    self.player.try_start_swing(aim_angle)

    # ---------- respawn / restart ----------
    def respawn_player(self):
        # try to handle music (optional)
        try:
            pygame.mixer.music.fadeout(1000)
            pygame.time.delay(1000)
            pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.play(-1, start=25.0, fade_ms=1500)
            pygame.mixer.music.set_volume(0.8)
        except Exception:
            pass

        self.respawn_count += 1
        if self.respawn_count == 1:
            self.knight_speed_scale = 0.8
        elif self.respawn_count == 2:
            self.knight_speed_scale = 0.6
        else:
            self.knight_speed_scale = 1.0
            self.respawn_count = 0

        # full heal on respawn (per your choice)
        self.player.health = PLAYER_MAX_HEALTH
        self.player.dead = False
        self.player.hit_flash = False
        self.player.death_time = None
        self.death_fade_start = None

        # center the player
        self.player.pos = pygame.Vector2(self.virtual_width // 2, self.virtual_height // 2)
        self.player.rect.center = (int(self.player.pos.x), int(self.player.pos.y))

        # apply speed multiplier to all existing knights
        for k in self.knights:
            k.speed = ENEMY_BASE_SPEED * self.knight_speed_scale

        # give short invincibility
        self.player.invincible = True
        self.player.invincibility_timer = 1000  # ms

    def restart_game(self):
        # reset counters and scale
        self.respawn_count = 0
        self.knight_speed_scale = 1.0

        # reset player
        self.player.health = PLAYER_MAX_HEALTH
        self.player.dead = False
        self.player.hit_flash = False
        self.player.invincible = False
        self.player.invincibility_timer = 0
        self.player.death_time = None
        self.death_fade_start = None
        self.player.pos = pygame.Vector2(self.virtual_width // 2, self.virtual_height // 2)
        self.player.rect.center = (int(self.player.pos.x), int(self.player.pos.y))

        # reset knights to original positions
        self.knights.clear()
        for pos in self.spawn_positions:
            k = Knight(pos[0], pos[1], self.player, self.bounds_rect, self.knights)
            k.speed = ENEMY_BASE_SPEED
            self.knights.append(k)

    # ---------- update ----------
    def update(self, dt):
        keys = pygame.key.get_pressed()

        # don't update world while a menu is up
        if self.show_retry or self.show_restart:
            return

        # update player
        self.player.update(keys, self.bounds_rect, dt)

        # player sword hit checks
        now = pygame.time.get_ticks()
        if self.player.swinging:
            elapsed = now - self.player.swing_start_time
            t = elapsed / max(1, self.player.swing_duration)
            arc = math.radians(100)
            offset = -arc / 2 + arc * t
            sword_angle = self.player.locked_angle + offset
            tip = pygame.Vector2(self.player.pos.x + math.cos(sword_angle) * self.player.sword_length,
                                 self.player.pos.y + math.sin(sword_angle) * self.player.sword_length)
            for knight in list(self.knights):
                kx, ky = knight.rect.center
                if math.hypot(kx - tip.x, ky - tip.y) <= PLAYER_SWORD_HIT_RADIUS:
                    knight.take_damage(SWORD_DAMAGE)
                    if knight.health <= 0:
                        # heal player a small amount on kill (1/10 of KNIGHT_DAMAGE, minimum 1)
                        heal_amount = max(1, int(KNIGHT_DAMAGE / 10))
                        self.player.health = min(PLAYER_MAX_HEALTH, self.player.health + heal_amount)
                        try:
                            self.knights.remove(knight)
                        except ValueError:
                            pass

        # update knights
        for k in list(self.knights):
            k.update()

        # respawn additional knights until we reach original count; newly spawned knights use current speed scale
        desired = len(self.spawn_positions)
        while len(self.knights) < desired:
            pos = random.choice(self.spawn_positions)
            k = Knight(pos[0], pos[1], self.player, self.bounds_rect, self.knights)
            k.speed = ENEMY_BASE_SPEED * self.knight_speed_scale
            self.knights.append(k)

        # handle player death -> start fade & schedule showing menus
        if self.player.health <= 0 and not self.player.dead:
            self.player.dead = True
            self.death_fade_start = pygame.time.get_ticks()
            return

        if self.player.dead:
            if self.death_fade_start is None:
                self.death_fade_start = pygame.time.get_ticks()
            else:
                elapsed = pygame.time.get_ticks() - self.death_fade_start
                if elapsed > DEATH_FADE_DURATION:
                    # third death = restart menu, otherwise respawn menu
                    if self.respawn_count >= 2:
                        self.show_restart = True
                    else:
                        self.show_retry = True
                    return

        # colors
        now = pygame.time.get_ticks()
        if now - self.last_color_change > self.color_interval:
            indices = [i for i in range(len(NEON_COLORS)) if i != self.color_index]
            self.color_index = random.choice(indices)
            self.border_color, self.floor_color = NEON_COLORS[self.color_index]
            self.pulse_start = now
            self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)
            self.last_color_change = now

    # ---------- draw ----------
    def draw(self):
        scale_x = self.window_width / self.virtual_width
        scale_y = self.window_height / self.virtual_height

        # background / border
        self.screen.fill(self.floor_color)
        pygame.draw.rect(self.screen, self.border_color,
                         pygame.Rect(0, 0, self.window_width, self.window_height), BORDER_THICKNESS)

        # afterimages
        for a in list(self.player.afterimages):
            alpha = a.get_alpha()
            if alpha <= 0:
                try:
                    self.player.afterimages.remove(a)
                except ValueError:
                    pass
                continue
            surf = pygame.Surface((PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y), pygame.SRCALPHA)
            surf.fill((255, 255, 255, alpha))
            pos = (a.pos[0] * scale_x - PLAYER_SIZE * scale_x / 2,
                   a.pos[1] * scale_y - PLAYER_SIZE * scale_y / 2)
            self.screen.blit(surf, pos)

        # health bar
        hp_percent = max(0.0, min(1.0, self.player.health / PLAYER_MAX_HEALTH))
        bar_rect = pygame.Rect(10, 10, int(200 * hp_percent), 20)
        bar_color = (int(255 * (1 - hp_percent)), int(255 * hp_percent), 0)
        pygame.draw.rect(self.screen, bar_color, bar_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), (10, 10, 200, 20), 2)

        # player and knights
        self.player.draw(self.screen, scale_x, scale_y)
        for k in self.knights:
            k.draw(self.screen, scale_x, scale_y)

        # pulse overlay
        if self.pulse_start:
            elapsed = pygame.time.get_ticks() - self.pulse_start
            if elapsed < PULSE_DURATION:
                alpha = int(PULSE_ALPHA * (1 - elapsed / PULSE_DURATION))
                alpha = max(0, min(255, alpha))
                if alpha > 0:
                    overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                    overlay.fill((*self.pulse_color, alpha))
                    self.screen.blit(overlay, (0, 0))
            else:
                self.pulse_start = None

        # hit flash overlay
        if self.player.hit_flash:
            elapsed = pygame.time.get_ticks() - self.player.hit_time
            if elapsed < HIT_FLASH_DURATION:
                alpha = int(150 * (1 - elapsed / HIT_FLASH_DURATION))
                alpha = max(0, min(255, alpha))
                if alpha > 0:
                    overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                    overlay.fill((255, 0, 0, alpha))
                    self.screen.blit(overlay, (0, 0))
            else:
                self.player.hit_flash = False

        # death fade overlay
        if self.player.dead and self.death_fade_start is not None:
            elapsed = pygame.time.get_ticks() - self.death_fade_start
            progress = min(1.0, elapsed / DEATH_FADE_DURATION)
            fade_alpha = min(255, int(255 * progress))
            overlay = pygame.Surface((self.window_width, self.window_height))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(fade_alpha)
            self.screen.blit(overlay, (0, 0))

        # draw menu UI if needed
        if self.show_retry or self.show_restart:
            font = pygame.font.SysFont(None, 72)
            small_font = pygame.font.SysFont(None, 36)
            if self.show_restart:
                title = font.render("GAME OVER", True, (220, 40, 40))
                opt1 = small_font.render("[R] Restart", True, (255, 255, 255))
                opt2 = small_font.render("[M] Menu", True, (200, 200, 200))
            else:
                title = font.render("YOU DIED", True, (220, 40, 40))
                opt1 = small_font.render("[R] Respawn", True, (255, 255, 255))
                opt2 = small_font.render("[M] Menu", True, (200, 200, 200))

            cx = self.window_width // 2
            cy = self.window_height // 2
            self.screen.blit(title, (cx - title.get_width() // 2, cy - 100))
            self.screen.blit(opt1, (cx - opt1.get_width() // 2, cy))
            self.screen.blit(opt2, (cx - opt2.get_width() // 2, cy + 48))

        pygame.display.flip()

    # ---------- run ----------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()


# ---------------- Run Game ----------------
if __name__ == "__main__":
    Game().run()
