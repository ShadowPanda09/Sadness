import pygame
import sys
import random
import math
import os
from levels import boss_level

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

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # Basic stats
        self.health = PLAYER_MAX_HEALTH
        self.dead = False
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(self.rect.center)

        # Invincibility
        self.invincible = False
        self.invincibility_timer = 0

        # Ability cooldown
        self.ability_cooldown = 5000  # ms
        self.last_ability_use = -self.ability_cooldown

        # Assassin invisibility
        self.invisible = False
        self.invisibility_timer = 0
        self.invisibility_duration = 3000  # ms

        # Player movement
        self.speed = 3
        self.facing = pygame.Vector2(0, 1)

        # Sword
        self.swinging = False
        self.swing_start_time = 0
        self.swing_cooldown = PLAYER_SWING_COOLDOWN_MS
        self.last_swing = -PLAYER_SWING_COOLDOWN_MS
        self.locked_angle = 0.0
        self.sword_length = PLAYER_SWORD_LENGTH
        self.swing_duration = PLAYER_SWING_DURATION_MS
        self.sword_trails = []

        # Hit flash
        self.hit_flash = False
        self.hit_time = 0
        self.death_time = None

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

        # Classes
        self.classes = ["Normal", "Healer", "Assassin", "Juggernaut"]
        self.class_index = 0
        self.class_type = self.classes[self.class_index]
        self.class_name = self.class_type
        self.apply_class_properties()

        # Juggernaut
        self.juggernaut_active = False
        self.juggernaut_start = 0
        self.juggernaut_duration = 500  # ms
        self.juggernaut_radius = 0
        self.juggernaut_max_radius = 250
        self.juggernaut_stun_duration = 1000  # ms
        self.juggernaut_color = (255, 255, 255)

    def apply_class_properties(self):
        """Apply stats based on current class."""
        if self.class_type == "Normal":
            self.speed = 3
            self.swing_duration = 150
            self.sword_length = 60
            self.damage = SWORD_DAMAGE
        elif self.class_type == "Healer":
            self.speed = 2.8
            self.swing_duration = 200
            self.sword_length = 50
            self.damage = SWORD_DAMAGE - 10
        elif self.class_type == "Assassin":
            self.speed = 3.5
            self.swing_duration = 120
            self.sword_length = 70
            self.damage = SWORD_DAMAGE + 10
        elif self.class_type == "Juggernaut":
            self.speed = 2
            self.swing_duration = 180
            self.sword_length = 80
            self.damage = SWORD_DAMAGE + 5

    def switch_class(self, direction):
        self.class_index = (self.class_index + direction) % len(self.classes)
        self.class_type = self.classes[self.class_index]
        self.class_name = self.class_type
        self.apply_class_properties()

    def use_ability(self):
        now = pygame.time.get_ticks()
        if now - self.last_ability_use < self.ability_cooldown or self.dead:
            return
        self.last_ability_use = now

        if self.class_type == "Healer":
            heal_amount = int(PLAYER_MAX_HEALTH * 0.25)
            self.health = min(PLAYER_MAX_HEALTH, self.health + heal_amount)
            self.hit_flash = True
            self.hit_time = now
        elif self.class_type == "Assassin":
            self.invisible = True
            self.invisibility_timer = self.invisibility_duration
        elif self.class_type == "Juggernaut":
            self.juggernaut_active = True
            self.juggernaut_start = now
            self.juggernaut_radius = 0

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
        self.swinging = False

    def try_start_swing(self, aim_angle):
        now = pygame.time.get_ticks()
        if self.dead or self.is_dashing or (self.swinging or now - self.last_swing < self.swing_cooldown):
            return
        self.swinging = True
        self.swing_start_time = now
        self.last_swing = now
        self.locked_angle = aim_angle
        tip = (self.pos.x + math.cos(self.locked_angle) * self.sword_length,
               self.pos.y + math.sin(self.locked_angle) * self.sword_length)
        self.sword_trails.append(SwordTrail((self.pos.x, self.pos.y), tip))

    def update_dash(self, dt_ms):
        if not self.is_dashing:
            return
        now = pygame.time.get_ticks()
        self.pos += self.dash_dir * DASH_SPEED
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        if now >= self._next_afterimage_at and len(self.afterimages) < DASH_FRAMES:
            self.afterimages.append(AfterImage(self.pos, len(self.afterimages)+1, DASH_FRAMES))
            self._next_afterimage_at = now + (DASH_COOLDOWN // DASH_FRAMES)
        self.dash_progress += 1
        if self.dash_progress >= DASH_FRAMES:
            self.is_dashing = False
            self.dash_progress = 0
            self.afterimages.clear()

    def update(self, keys, bounds_rect, dt_ms):
        now = pygame.time.get_ticks()
        # Movement
        move_vec = pygame.Vector2(0,0)
        if not self.is_dashing and not self.swinging:
            if keys[pygame.K_w]: move_vec.y -= 1
            if keys[pygame.K_s]: move_vec.y += 1
            if keys[pygame.K_a]: move_vec.x -= 1
            if keys[pygame.K_d]: move_vec.x += 1
            if move_vec.length_squared() > 0:
                if abs(move_vec.x) > 0 and abs(move_vec.y) > 0:
                    move_vec.y = 0
                self.facing = move_vec.normalize()
                self.pos += move_vec.normalize() * self.speed
                self.rect.center = self.pos
                self.rect.clamp_ip(bounds_rect)
                self.pos = pygame.Vector2(self.rect.center)
        # Dash
        if keys[pygame.K_LSHIFT]:
            if not self.dash_key_pressed: self.try_start_dash()
            self.dash_key_pressed = True
        else: self.dash_key_pressed = False
        if self.is_dashing:
            self.update_dash(dt_ms)
        # Swing
        if self.swinging:
            elapsed = now - self.swing_start_time
            if elapsed >= self.swing_duration:
                self.swinging = False
            else:
                t = elapsed / self.swing_duration
                arc = math.radians(100)
                offset = -arc/2 + arc * t
                sword_angle = self.locked_angle + offset
                tip = (self.pos.x + math.cos(sword_angle)*self.sword_length,
                       self.pos.y + math.sin(sword_angle)*self.sword_length)
                self.sword_trails.append(SwordTrail((self.pos.x, self.pos.y), tip))
                if len(self.sword_trails) > TRAIL_MAX_POINTS:
                    self.sword_trails.pop(0)
        # Invincibility / Invisibility timers
        if self.invincible:
            self.invincibility_timer -= dt_ms
            if self.invincibility_timer <= 0: self.invincible = False
        if self.invisible:
            self.invisibility_timer -= dt_ms
            if self.invisibility_timer <= 0: self.invisible = False
        if self.swinging and self.invisible:
            self.invisible = False
            self.invisibility_timer = 0

    def draw(self, surface, scale_x=1, scale_y=1):
        now = pygame.time.get_ticks()
        # Juggernaut pulse
        if self.juggernaut_active:
            elapsed = now - self.juggernaut_start
            t = elapsed / self.juggernaut_duration
            if t > 1:
                self.juggernaut_active = False
                self.juggernaut_radius = 0
            else:
                self.juggernaut_radius = int(self.juggernaut_max_radius * t)
                pygame.draw.circle(surface, self.juggernaut_color, self.rect.center, self.juggernaut_radius, 3)
        # Afterimages
        for afterimage in self.afterimages[:]:
            alpha = afterimage.get_alpha()
            if alpha <= 0:
                try: self.afterimages.remove(afterimage)
                except ValueError: pass
                continue
            surf = pygame.Surface((PLAYER_SIZE*scale_x, PLAYER_SIZE*scale_y), pygame.SRCALPHA)
            surf.fill((255,255,255,alpha))
            pos = (afterimage.pos[0]*scale_x, afterimage.pos[1]*scale_y)
            surface.blit(surf, (pos[0]-PLAYER_SIZE*scale_x/2, pos[1]-PLAYER_SIZE*scale_y/2))
        # Player
        alpha = 100 if self.invisible else 255
        surf = pygame.Surface((PLAYER_SIZE*scale_x, PLAYER_SIZE*scale_y), pygame.SRCALPHA)
        surf.fill((255,255,255,alpha))
        surface.blit(surf, (self.rect.x*scale_x, self.rect.y*scale_y))
        # Sword trails
        for trail in list(self.sword_trails):
            alpha = trail.get_alpha()
            if alpha <= 0:
                try: self.sword_trails.remove(trail)
                except ValueError: pass
                continue
            sx, sy = trail.start
            ex, ey = trail.end
            sx *= scale_x; sy *= scale_y; ex *= scale_x; ey *= scale_y
            surf_trail = pygame.Surface((abs(int(ex-sx))+6, abs(int(ey-sy))+6), pygame.SRCALPHA)
            pygame.draw.line(surf_trail, (255,255,255,alpha), (0 if ex>=sx else abs(int(ex-sx)),0 if ey>=sy else abs(int(ey-sy))),
                             (abs(int(ex-sx)) if ex>=sx else 0, abs(int(ey-sy)) if ey>=sy else 0), 3)
            surface.blit(surf_trail, (int(min(sx,ex))-2, int(min(sy,ey))-2))
        # Current sword swing
        if self.swinging:
            elapsed = now - self.swing_start_time
            t = elapsed / self.swing_duration if self.swing_duration else 1
            arc = math.radians(100)
            offset = -arc/2 + arc*t
            sword_angle = self.locked_angle + offset
            tip = (self.rect.centerx + math.cos(sword_angle)*self.sword_length*scale_x,
                   self.rect.centery + math.sin(sword_angle)*self.sword_length*scale_y)
            pygame.draw.line(surface, (255,255,255), self.rect.center, tip, 4)



class Knight(pygame.sprite.Sprite):
    def __init__(self, x, y, target, bounds_rect, all_knights):
        super().__init__()
        self.start_pos = pygame.Vector2(x, y)
        # keep same rectangle sprite as before
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill((200, 50, 50))
        self.rect = self.image.get_rect(center=(x, y))

        self.pos = pygame.Vector2(self.rect.center)
        self.speed = 3.75
        self.target = target
        self.bounds_rect = bounds_rect
        self.all_knights = all_knights

        self.health = 60
        self.hit_flash = False
        self.hit_time = 0

        # Attack visuals/state
        self.attack_range = 60
        self.last_attack = -1000
        self.attack_cooldown = 1000
        self.attacking = False
        self.attack_start_time = 0
        self.attack_duration = 300  # ms for visible attack
        self.attack_angle = 0.0
        self.attack_arc = math.radians(90)  # sweep arc
        self.attack_length = 80
        self.attack_damage = KNIGHT_DAMAGE

        # optional simple sword trail list (kept minimal)
        self.sword_trails = []

    def update(self):
        if getattr(self, "stunned", False):
            if pygame.time.get_ticks() >= getattr(self, "stun_end_time", 0):
                self.stunned = False
            else:
                return
        # dead knights don't act
        if getattr(self, "alive", True) is False:
            return
        now = pygame.time.get_ticks()
        dx = self.target.rect.centerx - self.rect.centerx
        dy = self.target.rect.centery - self.rect.centery
        distance = math.hypot(dx, dy)
        # If player is invisible, skip movement and attacking
        if getattr(self.target, "invisible", False):
            # Optional: you can still have knights idle or wander randomly if desired
            return

        # If currently performing an attack animation
        if self.attacking:
            elapsed = now - self.attack_start_time
            if elapsed > self.attack_duration:
                self.attacking = False
            else:
                # During the active attack window, check for hit (once)
                # We'll allow a hit at any time while attacking but guard with a last_attack timestamp
                # Check distance and cone
                if distance <= self.attack_range:
                    player_angle = math.atan2(dy, dx)
                    angle_diff = abs((player_angle - self.attack_angle + math.pi) % (2 * math.pi) - math.pi)
                    if angle_diff <= self.attack_arc / 2:
                        # Apply damage using Player's existing fields (no player.take_damage)
                        # NOTE: use self.target (the player) to check invincibility
                        if not self.target.hit_flash:
                            self.target.hit_flash = True
                            self.target.hit_time = now
                            # Check the target's invincibility state (use self.target.invincible)
                            if not getattr(self.target, "invincible", False):
                                self.target.health -= self.attack_damage
                                if self.target.health <= 0:
                                    self.target.health = 0
                                    self.target.dead = True
                                    # record death time if Player uses it
                                    self.target.death_time = pygame.time.get_ticks()
                            # ensure we don't repeatedly apply the same attack instantly:
                            # move last_attack forward so cooldown prevents re-triggering until next planned attack
                            self.last_attack = now
                return

        # If in range and cooldown elapsed, start attack
        if distance <= self.attack_range and (now - self.last_attack) >= self.attack_cooldown:
            self.attacking = True
            self.attack_start_time = now
            self.attack_angle = math.atan2(dy, dx)
            self.last_attack = now
            return

        # Movement toward player with avoidance (same behavior as before)
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
            # frame-rate friendly-ish movement (matches your prior pattern)
            self.pos += move_dir * (self.speed * (1.0 / (FPS / 60)))
            self.rect.center = (int(self.pos.x), int(self.pos.y))
            self.rect.clamp_ip(self.bounds_rect)
            self.pos = pygame.Vector2(self.rect.center)

    def take_damage(self, amount):
        # called by player sword; keep existing behavior
        self.health -= amount
        self.hit_flash = True
        self.hit_time = pygame.time.get_ticks()

    def draw(self, surface, scale_x=1, scale_y=1):
        # draw the rectangle knight (unchanged visual)
        color = (255, 120, 120) if self.hit_flash else (200, 50, 50)
        scaled_rect = pygame.Rect(
            self.rect.x * scale_x,
            self.rect.y * scale_y,
            PLAYER_SIZE * scale_x,
            PLAYER_SIZE * scale_y
        )
        pygame.draw.rect(surface, color, scaled_rect)

        # draw attack animation arc if attacking
        if self.attacking:
            elapsed = pygame.time.get_ticks() - self.attack_start_time
            progress = elapsed / max(1, self.attack_duration)
            # compute alpha and clamp to valid 0..255
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
        # clear hit flash after a short time
        if self.hit_flash and (pygame.time.get_ticks() - self.hit_time) > HIT_FLASH_DURATION:
            self.hit_flash = False


class Game:
    def __init__(self):
        # respawn counter & speed scale
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

        # spawn positions / knights
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

        # colors / pulses
        self.color_index = random.randrange(len(NEON_COLORS))
        self.border_color, self.floor_color = NEON_COLORS[self.color_index]
        self.last_color_change = pygame.time.get_ticks()
        self.color_interval = 3000
        self.pulse_start = None
        self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)

        # death / menu states
        self.death_fade_start = None
        self.show_retry = False       # first/second-death respawn menu
        self.show_restart = False     # third-death "Restart / Menu" menu
        self.show_menu_button = False
        self.knight_kills = 0
        self.PASSING_KILLS = 0
        self.transition_to_boss = False
        self.transition_start = 0
        self.TRANSITION_DURATION = 500  # milliseconds for fast transition
        self.boss_launched = False  # prevent multiple launches

    # ---------------- handle events ----------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.VIDEORESIZE:
                self.window_width, self.window_height = event.w, event.h
                self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

            # If a menu is showing, let its keys take precedence
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
                continue

            # Normal game inputs
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LSHIFT:
                    self.player.try_start_dash()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    aim_angle = math.atan2(my - self.player.rect.centery, mx - self.player.rect.centerx)
                    self.player.try_start_swing(aim_angle)
                elif event.button == 4:
                    self.player.switch_class(1)
                elif event.button == 5:
                    self.player.switch_class(-1)
                elif event.button == 3:
                    self.player.use_ability()

    # ---------------- respawn / restart helpers ----------------
    def respawn_player(self):
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

        self.player.health = PLAYER_MAX_HEALTH
        self.player.dead = False
        self.player.hit_flash = False
        self.player.death_time = None
        self.death_fade_start = None
        self.player.pos = pygame.Vector2(self.virtual_width // 2, self.virtual_height // 2)
        self.player.rect.center = (int(self.player.pos.x), int(self.player.pos.y))

        for k in self.knights:
            k.speed = 3.75 * self.knight_speed_scale

        self.player.invincible = True
        self.player.invincibility_timer = 1000

    def restart_game(self):
        self.respawn_count = 0
        self.knight_speed_scale = 1.0
        self.player.health = PLAYER_MAX_HEALTH
        self.player.dead = False
        self.player.hit_flash = False
        self.player.death_time = None
        self.death_fade_start = None
        self.player.pos = pygame.Vector2(self.virtual_width // 2, self.virtual_height // 2)
        self.player.rect.center = (int(self.player.pos.x), int(self.player.pos.y))

        self.knights.clear()
        for pos in self.spawn_positions:
            k = Knight(pos[0], pos[1], self.player, self.bounds_rect, self.knights)
            k.speed = 3.75
            self.knights.append(k)

    # ---------------- boss launch helper ----------------
    def launch_boss_level(self):
        if self.boss_launched:
            return
        self.boss_launched = True
        try:
            boss_level.BossLevel().run()
        except Exception as ex:
            print("Failed to launch boss level", ex)
        finally:
            self.running = False

    # ---------------- update ----------------
    def update(self, dt):
        # handle boss transition
        if self.transition_to_boss:
            elapsed = pygame.time.get_ticks() - self.transition_start
            if elapsed >= self.TRANSITION_DURATION:
                self.launch_boss_level()
                return
            # freeze game world during transition
            return

        keys = pygame.key.get_pressed()
        if self.show_retry or self.show_restart:
            return

        self.player.update(keys, self.bounds_rect, dt)

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
                        try:
                            self.knights.remove(knight)
                        except ValueError:
                            pass
                        self.knight_kills += 1
                        if self.knight_kills >= self.PASSING_KILLS:
                            self.transition_to_boss = True
                            self.transition_start = pygame.time.get_ticks()

        for k in list(self.knights):
            k.update()

        while len(self.knights) < len(self.spawn_positions):
            pos = random.choice(self.spawn_positions)
            k = Knight(pos[0], pos[1], self.player, self.bounds_rect, self.knights)
            k.speed = 3.75 * self.knight_speed_scale
            self.knights.append(k)

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
                    if self.respawn_count >= 2:
                        self.show_restart = True
                    else:
                        self.show_retry = True
                    return

        # color pulse logic
        if now - self.last_color_change > self.color_interval:
            indices = [i for i in range(len(NEON_COLORS)) if i != self.color_index]
            self.color_index = random.choice(indices)
            self.border_color, self.floor_color = NEON_COLORS[self.color_index]
            self.pulse_start = now
            self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)
            self.last_color_change = now

    # ---------------- draw ----------------
    def draw(self):
        if not pygame.display.get_surface():
            return  # prevent drawing if surface gone (safe for boss launch)

        scale_x = self.window_width / self.virtual_width
        scale_y = self.window_height / self.virtual_height

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

        self.player.draw(self.screen, scale_x, scale_y)
        for k in self.knights:
            k.draw(self.screen, scale_x, scale_y)

        # overlay pulses & death fade (same as before)...
        if self.transition_to_boss:
            elapsed = pygame.time.get_ticks() - self.transition_start
            alpha = int(255 * (elapsed / self.TRANSITION_DURATION))
            alpha = max(0, min(255, alpha))
            overlay = pygame.Surface((self.window_width, self.window_height))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(alpha)
            self.screen.blit(overlay, (0, 0))

        pygame.display.flip()

    # ---------------- run ----------------
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
