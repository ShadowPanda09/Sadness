import pygame
import sys
import random
import math

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

# -------------------------- Classes --------------------------

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
        self.health = PLAYER_MAX_HEALTH
        self.dead = False
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill((255, 255, 255))
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(self.rect.center)  # float position

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

        self.facing = pygame.Vector2(0, 1)
        self.dash_key_pressed = False

        # Sword
        self.swinging = False
        self.swing_start_time = 0
        self.swing_duration = PLAYER_SWING_DURATION_MS
        self.swing_cooldown = PLAYER_SWING_COOLDOWN_MS
        self.last_swing = -PLAYER_SWING_COOLDOWN_MS
        self.locked_angle = 0.0  # angle at start of swing (radians)
        self.sword_length = PLAYER_SWORD_LENGTH
        self.sword_trails = []

        # hit
        self.hit_flash = False
        self.hit_time = 0
        self.death_time = None

    def try_start_dash(self):
        now = pygame.time.get_ticks()
        if self.dead or self.is_dashing:
            return
        if (now - self.last_dash) < self.dash_cooldown:
            return
        # Use facing direction (set from movement) - if zero, default up
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
        # cancel swing if any
        self.swinging = False

    def try_start_swing(self, aim_angle):
        now = pygame.time.get_ticks()
        if self.dead:
            return
        if self.is_dashing:
            return
        if (now - self.last_swing) >= self.swing_cooldown and not self.swinging:
            self.swinging = True
            self.swing_start_time = now
            self.last_swing = now
            self.locked_angle = aim_angle
            # add initial trail point
            tip = (self.pos.x + math.cos(self.locked_angle) * self.sword_length,
                   self.pos.y + math.sin(self.locked_angle) * self.sword_length)
            self.sword_trails.append(SwordTrail((self.pos.x, self.pos.y), tip))

    def update_dash(self, dt_ms):
        if not self.is_dashing:
            return
        now = pygame.time.get_ticks()
        elapsed = now - self.dash_start_time
        if elapsed <=  (DASH_FRAMES * (DASH_COOLDOWN // DASH_FRAMES)) or True:
            # move per frame using DASH_SPEED pixels per frame (keeps behavior consistent)
            self.pos += self.dash_dir * DASH_SPEED
            self.rect.center = (int(self.pos.x), int(self.pos.y))
            # spawn afterimages at simple intervals (frame-based)
            if now >= self._next_afterimage_at and len(self.afterimages) < DASH_FRAMES:
                self.afterimages.append(AfterImage(self.pos, len(self.afterimages) + 1, DASH_FRAMES))
                self._next_afterimage_at = now + (DASH_COOLDOWN // max(1, DASH_FRAMES))
        # End dash after fixed frames
        self.dash_progress += 1
        if self.dash_progress >= DASH_FRAMES:
            self.is_dashing = False
            self.dash_progress = 0
            self.afterimages.clear()

    def update(self, keys, bounds_rect, dt_ms):
        now = pygame.time.get_ticks()

        # dash input (LSHIFT starts dash)
        if keys[pygame.K_LSHIFT]:
            # try to start dash on press edge
            if not self.dash_key_pressed:
                self.try_start_dash()
            self.dash_key_pressed = True
        else:
            self.dash_key_pressed = False

        # movement when not dashing
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
                # prefer cardinal directions if both pressed (match prior behavior)
                if abs(move_vec.x) > 0 and abs(move_vec.y) > 0:
                    move_vec.y = 0
                self.facing = move_vec.normalize()
                self.pos += move_vec.normalize() * self.speed
                self.rect.center = (int(self.pos.x), int(self.pos.y))
                self.rect.clamp_ip(bounds_rect)
                self.pos = pygame.Vector2(self.rect.center)

        # dash update (frame-based)
        if self.is_dashing:
            # move by dash speed
            self.pos += self.dash_dir * DASH_SPEED
            self.rect.center = (int(self.pos.x), int(self.pos.y))
            self.rect.clamp_ip(bounds_rect)
            # afterimage spawn
            if now >= self._next_afterimage_at and len(self.afterimages) < DASH_FRAMES:
                self.afterimages.append(AfterImage(self.pos, len(self.afterimages) + 1, DASH_FRAMES))
                self._next_afterimage_at = now + max(1, int(self.swing_duration / max(1, DASH_FRAMES)))
            # simple frame-limit for dash (DASH_FRAMES increments)
            self.dash_progress += 1
            if self.dash_progress >= DASH_FRAMES:
                self.is_dashing = False
                self.dash_progress = 0
                self.afterimages.clear()

        # Swing update (creates sweeping arc + trails)
        if self.swinging:
            elapsed = now - self.swing_start_time
            if elapsed >= self.swing_duration:
                self.swinging = False
            else:
                t = elapsed / self.swing_duration  # 0..1
                arc = math.radians(100)  # total sweep angle
                offset = -arc / 2 + arc * t
                sword_angle = self.locked_angle + offset
                start = (self.pos.x, self.pos.y)
                tip = (start[0] + math.cos(sword_angle) * self.sword_length,
                       start[1] + math.sin(sword_angle) * self.sword_length)
                self.sword_trails.append(SwordTrail(start, tip))
                if len(self.sword_trails) > TRAIL_MAX_POINTS:
                    self.sword_trails.pop(0)

    def draw(self, surface, scale_x=1, scale_y=1):
        # draw afterimages
        for afterimage in self.afterimages[:]:
            alpha = afterimage.get_alpha()
            if alpha <= 0:
                try: self.afterimages.remove(afterimage)
                except ValueError: pass
                continue
            surf = pygame.Surface((PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y), pygame.SRCALPHA)
            surf.fill((255, 255, 255, alpha))
            pos = (afterimage.pos[0] * scale_x, afterimage.pos[1] * scale_y)
            surface.blit(surf, (pos[0] - PLAYER_SIZE * scale_x / 2, pos[1] - PLAYER_SIZE * scale_y / 2))

        # draw player
        scaled_rect = pygame.Rect(self.rect.x * scale_x, self.rect.y * scale_y,
                                  PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y)
        pygame.draw.rect(surface, (255, 255, 255), scaled_rect)

        # draw current sword arc (if swinging) as a single thicker white arc line
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

        # draw sword trails
        for trail in list(self.sword_trails):
            alpha = trail.get_alpha()
            if alpha <= 0:
                try: self.sword_trails.remove(trail)
                except ValueError: pass
                continue
            sx, sy = trail.start
            ex, ey = trail.end
            # scale coordinates
            sx *= scale_x; sy *= scale_y; ex *= scale_x; ey *= scale_y
            # draw trail segment
            surf = pygame.Surface((abs(int(ex - sx)) + 6, abs(int(ey - sy)) + 6), pygame.SRCALPHA)
            pygame.draw.line(surf, (255, 255, 255, alpha), ( (0 if ex>=sx else abs(int(ex-sx))), (0 if ey>=sy else abs(int(ey-sy))) ), ( (abs(int(ex - sx)) if ex>=sx else 0), (abs(int(ey - sy)) if ey>=sy else 0) ), 3)
            # blit at min point
            min_x = int(min(sx, ex)) - 2
            min_y = int(min(sy, ey)) - 2
            surface.blit(surf, (min_x, min_y))


class Knight(pygame.sprite.Sprite):
    def __init__(self, x, y, target, bounds_rect, all_knights):
        super().__init__()
        self.start_pos = pygame.Vector2(x, y)
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

        # Attack
        self.attack_range = 60
        self.last_attack = -1000
        self.attack_cooldown = 1000

        # Sword trails (for enemy swings) kept minimal here
        self.sword_trails = []

    def update(self):
        now = pygame.time.get_ticks()
        dx = self.target.rect.centerx - self.rect.centerx
        dy = self.target.rect.centery - self.rect.centery
        distance = math.hypot(dx, dy)

        # Swing if in range
        if distance <= self.attack_range and (now - self.last_attack) >= self.attack_cooldown:
            # perform a simple attack (instant damage) and cooldown
            if not self.target.hit_flash:
                self.target.hit_flash = True
                self.target.hit_time = now
                self.target.health -= KNIGHT_DAMAGE
                if self.target.health <= 0:
                    self.target.health = 0
                    self.target.dead = True
            self.last_attack = now
            return

        # Movement towards player with avoidance
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
            self.pos += move_dir * (self.speed * (1.0 / (FPS/60)))  # frame-rate friendly-ish
            self.rect.center = (int(self.pos.x), int(self.pos.y))
            self.rect.clamp_ip(self.bounds_rect)
            self.pos = pygame.Vector2(self.rect.center)

    def take_damage(self, amount):
        self.health -= amount
        self.hit_flash = True
        self.hit_time = pygame.time.get_ticks()

    def draw(self, surface, scale_x=1, scale_y=1):
        color = (255, 120, 120) if self.hit_flash else (200, 50, 50)
        rect = pygame.Rect(self.rect.x * scale_x, self.rect.y * scale_y,
                           PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y)
        pygame.draw.rect(surface, color, rect)
        # clear hit flash after short time
        if self.hit_flash and (pygame.time.get_ticks() - self.hit_time) > HIT_FLASH_DURATION:
            self.hit_flash = False

# -------------------------- Game --------------------------

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

        # spawn knights in corners
        self.knights = []
        spawn_positions = [(40, 40), (self.virtual_width - 40, 40),
                           (40, self.virtual_height - 40), (self.virtual_width - 40, self.virtual_height - 40)]
        for pos in spawn_positions:
            k = Knight(pos[0], pos[1], self.player, self.bounds_rect, self.knights)
            self.knights.append(k)

        self.color_index = random.randrange(len(NEON_COLORS))
        self.border_color, self.floor_color = NEON_COLORS[self.color_index]
        self.last_color_change = pygame.time.get_ticks()
        self.color_interval = 3000
        self.pulse_start = None
        self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)
        self.death_fade_start = None
        self.show_retry = False   

    # ---------------- Handle Events ----------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.VIDEORESIZE:
                self.window_width, self.window_height = event.w, event.h
                self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

            # If death menu active, handle its keys / mouse first, and ignore game inputs
            if self.show_retry:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # Respawn
                        self.reset_game()
                        self.show_retry = False
                        return
                    elif event.key == pygame.K_m:  # Menu
                        import spiritbound_title
                        pygame.mixer.stop()
                        self.running = False
                        pygame.display.quit()
                        spiritbound_title.main_menu()
                        return
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # optional: allow clicking text/buttons if you later add rects
                    pass
                # While death menu shown, skip the rest of input processing
                continue

            # --- Normal game inputs when not in death menu ---
            elif event.type == pygame.KEYDOWN:
                # allow dash to start also on keydown
                if event.key == pygame.K_LSHIFT:
                    self.player.try_start_dash()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click -> swing toward mouse
                    mx, my = pygame.mouse.get_pos()
                    # convert mouse coords to virtual coords (no scaling implemented here so same)
                    aim_angle = math.atan2(my - self.player.rect.centery, mx - self.player.rect.centerx)
                    self.player.try_start_swing(aim_angle)

    # ---------------- Update ----------------
    def update(self, dt):
        keys = pygame.key.get_pressed()
        # update player (movement, dash, swing)
        self.player.update(keys, self.bounds_rect, dt)

        # Sword hitting knights: compute tip each frame during active swing and damage once per knight per swing
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
                if knight.rect.center:  # sanity
                    kx, ky = knight.rect.center
                    if math.hypot(kx - tip.x, ky - tip.y) <= PLAYER_SWORD_HIT_RADIUS:
                        # apply damage and remove or mark
                        knight.take_damage(SWORD_DAMAGE)
                        if knight.health <= 0:
                            try:
                                self.knights.remove(knight)
                            except ValueError:
                                pass

        # update knights
        for k in self.knights:
            k.update()
            if len(self.knights) < 4:
                spawn_positions = [(40, 40), (self.virtual_width - 40, 40),
                                (40, self.virtual_height - 40), (self.virtual_width - 40, self.virtual_height - 40)]
                while len(self.knights) < 4:
                    pos = random.choice(spawn_positions)
                    k = Knight(pos[0], pos[1], self.player, self.bounds_rect, self.knights)
                    self.knights.append(k)

        # handle player death
        if self.player.dead:
            if self.death_fade_start is None:
                # Start the fade timer
                self.death_fade_start = pygame.time.get_ticks()
            else:
                # Check how long it's been since death
                elapsed = pygame.time.get_ticks() - self.death_fade_start
                if elapsed > DEATH_FADE_DURATION:
                    self.show_retry = True
            return

        # color change
        now = pygame.time.get_ticks()
        if now - self.last_color_change > self.color_interval:
            indices = [i for i in range(len(NEON_COLORS)) if i != self.color_index]
            self.color_index = random.choice(indices)
            self.border_color, self.floor_color = NEON_COLORS[self.color_index]
            self.pulse_start = now
            self.pulse_color = tuple(min(255, c + 100) for c in self.border_color)
            self.last_color_change = now
    def show_death_menu(self):
        """Display simple death screen with Respawn/Menu options."""
        import spiritbound_title  # import here to avoid circular imports
        font = pygame.font.SysFont(None, 48)
        small_font = pygame.font.SysFont(None, 32)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # Respawn
                        self.reset_game()
                        return
                    elif event.key == pygame.K_m:  # Return to main menu
                        pygame.mixer.stop()
                        self.running = False
                        pygame.display.quit()
                        spiritbound_title.main_menu()
                        return

            # draw the death screen
            self.screen.fill((0, 0, 0))
            text = font.render("You Died", True, (255, 50, 50))
            respawn_text = small_font.render("[R] Respawn", True, (255, 255, 255))
            menu_text = small_font.render("[M] Menu", True, (200, 200, 200))

            self.screen.blit(text, (self.window_width // 2 - text.get_width() // 2,
                                    self.window_height // 2 - 100))
            self.screen.blit(respawn_text, (self.window_width // 2 - respawn_text.get_width() // 2,
                                            self.window_height // 2))
            self.screen.blit(menu_text, (self.window_width // 2 - menu_text.get_width() // 2,
                                         self.window_height // 2 + 40))

            pygame.display.flip()
            self.clock.tick(30)

    # ---------------- Draw ----------------
    def draw(self):
        if self.death_fade_start is None:
            self.death_fade_start = 0 

        scale_x = self.window_width / self.virtual_width
        scale_y = self.window_height / self.virtual_height

        # background
        self.screen.fill(self.floor_color)
        pygame.draw.rect(self.screen, self.border_color,
                         pygame.Rect(0, 0, self.window_width, self.window_height), BORDER_THICKNESS)

        # afterimages
        for a in self.player.afterimages[:]:
            alpha = a.get_alpha()
            if alpha <= 0:
                try: self.player.afterimages.remove(a)
                except ValueError: pass
                continue
            surf = pygame.Surface((PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y), pygame.SRCALPHA)
            surf.fill((255, 255, 255, alpha))
            pos = (a.pos[0] * scale_x - PLAYER_SIZE * scale_x / 2,
                   a.pos[1] * scale_y - PLAYER_SIZE * scale_y / 2)
            self.screen.blit(surf, pos)

        # health bar
        hp_percent = max(0, min(1, self.player.health / PLAYER_MAX_HEALTH))
        bar_rect = pygame.Rect(10, 10, int(200 * hp_percent), 20)
        bar_color = (int(255 * (1 - hp_percent)), int(255 * hp_percent), 0)
        pygame.draw.rect(self.screen, bar_color, bar_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), (10, 10, 200, 20), 2)

        # player (and sword)
        self.player.draw(self.screen, scale_x, scale_y)

        # knights
        for k in self.knights:
            k.draw(self.screen, scale_x, scale_y)

        # pulse overlay
        if self.pulse_start:
            elapsed = pygame.time.get_ticks() - self.pulse_start
            if elapsed < PULSE_DURATION:
                alpha = int(PULSE_ALPHA * (1 - elapsed / PULSE_DURATION))
                overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                overlay.fill((*self.pulse_color, alpha))
                self.screen.blit(overlay, (0, 0))
            else:
                self.pulse_start = None

        # hit flash overlay (player)
        if self.player.hit_flash:
            elapsed = pygame.time.get_ticks() - self.player.hit_time
            if elapsed < HIT_FLASH_DURATION:
                alpha = int(150 * (1 - elapsed / HIT_FLASH_DURATION))
                overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                overlay.fill((255, 0, 0, alpha))
                self.screen.blit(overlay, (0, 0))
            else:
                self.player.hit_flash = False

        # death fade
        if self.player.dead and self.death_fade_start is not None:
            elapsed = pygame.time.get_ticks() - self.death_fade_start
            progress = min(1.0, elapsed / DEATH_FADE_DURATION)
            fade_alpha = min(255, int(255 * progress))
            overlay = pygame.Surface((self.window_width, self.window_height))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(fade_alpha)
            self.screen.blit(overlay, (0, 0))

        # If fade completed, draw the death menu overlay UI (non-blocking)
        if self.show_retry:
            font = pygame.font.SysFont(None, 72)
            small_font = pygame.font.SysFont(None, 36)
            title = font.render("YOU DIED", True, (220, 40, 40))
            respawn = small_font.render("[R] Respawn", True, (255, 255, 255))
            menu_txt = small_font.render("[M] Menu", True, (200, 200, 200))

            cx = self.window_width // 2
            cy = self.window_height // 2
            self.screen.blit(title, (cx - title.get_width() // 2, cy - 100))
            self.screen.blit(respawn, (cx - respawn.get_width() // 2, cy))
            self.screen.blit(menu_txt, (cx - menu_txt.get_width() // 2, cy + 48))

        pygame.display.flip()
    def reset_game(self):
        """Resets player and enemies after death."""
        self.player = Player(self.virtual_width // 2, self.virtual_height // 2)
        self.knights.clear()
        spawn_positions = [(40, 40), (self.virtual_width - 40, 40),
                           (40, self.virtual_height - 40), (self.virtual_width - 40, self.virtual_height - 40)]
        for pos in spawn_positions:
            k = Knight(pos[0], pos[1], self.player, self.bounds_rect, self.knights)
            self.knights.append(k)
        self.death_fade_start = None
        self.show_retry = False
    # ---------------- Run ----------------
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
