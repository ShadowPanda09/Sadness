import pygame
import sys
import random
import math
import spiritbound_title

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

# --- Death effect ---
DEATH_FADE_DURATION = 1000  # milliseconds for black fade

# --- Neon color palettes ---
NEON_COLORS = [
    ((0, 255, 180), (0, 100, 70)),
    ((0, 200, 255), (0, 80, 100)),
    ((140, 0, 255), (80, 0, 120)),
    ((0, 255, 120), (0, 100, 50)),
]

# Shockwave (ripple distortion) settings
RIPPLE_INTENSITY = 0.015  # higher = stronger warp
RIPPLE_WAVES = 5          # how many wave rings appear
RIPPLE_SPEED = 6.0        # how fast they move
RIPPLE_RES = 160  # much smaller than 640x480

# -------------------------- HEALTH --------------------------
PLAYER_MAX_HEALTH = 100
KNIGHT_DAMAGE = 15


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
        self.health = PLAYER_MAX_HEALTH
        self.dead = False
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
        self.start_pos = pygame.Vector2(x, y)
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
        self.image.fill((200, 50, 50))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 3.75
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
            # Sword swinging logic
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
                    if not self.target.hit_flash:
                        self.target.hit_flash = True
                        self.target.hit_time = now
                        self.target.health -= KNIGHT_DAMAGE
                        if self.target.health < 0:
                            self.target.health = 0
            return  # don't move while swinging

        # Start swing if in range
        if distance <= self.attack_range and now - self.last_swing >= self.swing_cooldown:
            self.swinging = True
            self.swing_start_time = now
            self.last_swing = now
            return

        # --- Movement toward player ---
        if distance > 0:
            to_player = pygame.Vector2(dx, dy).normalize()
        else:
            to_player = pygame.Vector2(0, 0)

        # --- Avoidance + detour movement ---
        avoidance = pygame.Vector2(0, 0)
        for other in self.all_knights:
            if other == self:
                continue
            offset = pygame.Vector2(self.rect.center) - pygame.Vector2(other.rect.center)
            dist = offset.length()
            if 0 < dist < PLAYER_SIZE * 1.5:
                # Push away from nearby knights
                offset.normalize_ip()
                avoidance += offset * ((PLAYER_SIZE * 1.5 - dist) / (PLAYER_SIZE * 1.5))

                # If directly ahead, curve sideways slightly
                forward_dot = to_player.dot(offset)
                if forward_dot < -0.3:  # knight ahead
                    perp = pygame.Vector2(-to_player.y, to_player.x)
                    avoidance += perp * random.choice([-1, 1]) * 0.3

        # Combine movement forces
        move_dir = to_player + avoidance
        if move_dir.length() > 0:
            move_dir.normalize_ip()
            

            
            move = move_dir * self.speed
            # --- CROWD SLOWDOWN ---
            nearby_count = 0
            for other in self.all_knights:
                if other == self:
                    continue
                if self.rect.centerx - PLAYER_SIZE*2 < other.rect.centerx < self.rect.centerx + PLAYER_SIZE*2 and \
                self.rect.centery - PLAYER_SIZE*2 < other.rect.centery < self.rect.centery + PLAYER_SIZE*2:
                    nearby_count += 1
            crowd_factor = max(0.5, 1 - 0.1 * nearby_count)  # slows more with density
            move = move_dir * self.speed * crowd_factor

            self.rect.x += move.x
            self.rect.y += move.y

        # --- Keep inside bounds ---
        if self.rect.left < self.bounds_rect.left + BORDER_THICKNESS:
            self.rect.left = self.bounds_rect.left + BORDER_THICKNESS
        if self.rect.right > self.bounds_rect.right - BORDER_THICKNESS:
            self.rect.right = self.bounds_rect.right - BORDER_THICKNESS
        if self.rect.top < self.bounds_rect.top + BORDER_THICKNESS:
            self.rect.top = self.bounds_rect.top + BORDER_THICKNESS
        if self.rect.bottom > self.bounds_rect.bottom - BORDER_THICKNESS:
            self.rect.bottom = self.bounds_rect.bottom - BORDER_THICKNESS



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

        self.menu_button_rect = pygame.Rect(self.window_width//2 - 60, self.window_height//2 + 100, 120, 40)
        self.show_menu_button = False

        self.death_fade_start = None
        self.show_retry = False
        self.retry_button_rect = pygame.Rect(self.window_width//2 - 60, self.window_height//2 + 50, 120, 40)

        self.bounds_rect = pygame.Rect(0, 0, self.virtual_width, self.virtual_height)
        self.player = Player(self.virtual_width // 2, self.virtual_height // 2)
        self.all_sprites = pygame.sprite.Group(self.player)

        self.knights = pygame.sprite.Group()
        # Pass reference to all_knights to each Knight
        for pos in [(0, 0), (0, self.virtual_height), (self.virtual_width, 0)]:
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
            elif self.player.dead:
                # --- Keyboard navigation for Undertale-style menu ---
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_UP, pygame.K_w]:
                        self.heart_index = (self.heart_index - 1) % 2
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.heart_index = (self.heart_index + 1) % 2
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        _, label = self.button_rects[self.heart_index]
                        if label == "Retry":
                            self.reset_game()
                        elif label == "Menu":
                            pygame.mixer.stop()
                            spiritbound_title.main_menu()
                            self.running = False
                            return

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    for rect, label in getattr(self, "button_rects", []):
                        if rect.collidepoint(event.pos):
                            if label == "Retry":
                                self.reset_game()
                            elif label == "Menu":
                                import spiritbound_title
                                pygame.mixer.stop()
                                spiritbound_title.main_menu()
                                self.running = False
                                return


    def reset_game(self):
        # Reset player
        self.player.health = PLAYER_MAX_HEALTH
        self.player.dead = False
        self.show_retry = False
        self.player.rect.center = (self.virtual_width // 2, self.virtual_height // 2)
        self.player.afterimages.clear()
        self.death_fade_start = None

        # Reset knights
        for knight in self.knights:
            knight.rect.center = knight.start_pos.xy
            knight.swinging = False
            knight.sword_trails.clear()
            knight.last_swing = -1000

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.player.update(keys, self.bounds_rect)
        if self.player.health <= 0 and not self.player.dead:
            self.player.dead = True
            self.death_fade_start = pygame.time.get_ticks()

        for knight in self.knights:
            knight.update()

        now = pygame.time.get_ticks()
        if now - self.last_color_change > self.color_interval:
            self.change_color()
            self.last_color_change = now

    def draw_undertale_death_menu(self):
        """Draws Undertale-style death menu with a red heart selector."""
        surface = self.screen
        WIDTH, HEIGHT = self.window_width, self.window_height

        # --- Faded gray overlay ---
        gray_overlay = pygame.Surface((WIDTH, HEIGHT))
        gray_overlay.fill((20, 20, 20))
        gray_overlay.set_alpha(200)
        surface.blit(gray_overlay, (0, 0))

        # --- Title text ---
        title_font = pygame.font.Font(None, 72)
        title_text = title_font.render("YOU DIED", True, (220, 40, 40))
        title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        surface.blit(title_text, title_rect)

        # --- Button setup ---
        button_font = pygame.font.Font(None, 48)
        options = ["Retry", "Menu"]
        spacing = 80
        start_y = HEIGHT // 2
        self.button_rects = []

        for i, label in enumerate(options):
            y = start_y + i * spacing
            rect = pygame.Rect(WIDTH // 2 - 100, y, 200, 50)
            self.button_rects.append((rect, label))

            hovered = rect.collidepoint(pygame.mouse.get_pos())
            border_color = (255, 255, 255) if not hovered else (255, 60, 60)
            pygame.draw.rect(surface, border_color, rect, 2)

            text_color = (255, 255, 255) if not hovered else (255, 80, 80)
            text = button_font.render(label, True, text_color)
            text_rect = text.get_rect(center=rect.center)
            surface.blit(text, text_rect)

        # --- Heart selector (Undertale style) ---
        self.heart_index = getattr(self, "heart_index", 0)
        heart_y = start_y + self.heart_index * spacing + 25
        pygame.draw.polygon(
            surface,
            (255, 0, 0),
            [
                (WIDTH // 2 - 130, heart_y - 10),
                (WIDTH // 2 - 122, heart_y),
                (WIDTH // 2 - 130, heart_y + 10)
            ]
        )

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

        # Floor
        self.screen.fill(self.floor_color)

        # Neon boundary
        pygame.draw.rect(self.screen, self.border_color,
                        pygame.Rect(offset_x, offset_y, self.window_width, self.window_height),
                        BORDER_THICKNESS)

        # --- Afterimages ---
        afterimage_surf = pygame.Surface((PLAYER_SIZE * scale_x, PLAYER_SIZE * scale_y), pygame.SRCALPHA)
        for afterimage in self.player.afterimages[:]:
            alpha = afterimage.get_alpha()
            if alpha <= 0:
                self.player.afterimages.remove(afterimage)
                continue
            afterimage_surf.fill((255, 255, 255, alpha))
            pos = (afterimage.pos[0] * scale_x + offset_x, afterimage.pos[1] * scale_y + offset_y)
            self.screen.blit(afterimage_surf, (pos[0] - PLAYER_SIZE * scale_x / 2, pos[1] - PLAYER_SIZE * scale_y / 2))

        # --- Health bar ---
        bar_width = 200
        bar_height = 20
        health_percent = self.player.health / PLAYER_MAX_HEALTH
        bar_color = (
            int(255 * (1 - health_percent)),
            int(255 * health_percent),
            0
        )
        bar_rect = pygame.Rect(10, 10, int(bar_width * health_percent), bar_height)
        pygame.draw.rect(self.screen, bar_color, bar_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), (10, 10, bar_width, bar_height), 2)

        # --- Player ---
        scaled_rect = pygame.Rect(
            self.player.rect.x * scale_x + offset_x,
            self.player.rect.y * scale_y + offset_y,
            PLAYER_SIZE * scale_x,
            PLAYER_SIZE * scale_y
        )
        pygame.draw.rect(self.screen, (255, 255, 255), scaled_rect)

        # --- Knights ---
        for knight in self.knights:
            knight.draw(self.screen, scale_x, scale_y)

        # --- Neon pulse overlay ---
        if self.pulse_start:
            elapsed = pygame.time.get_ticks() - self.pulse_start
            if elapsed < PULSE_DURATION:
                alpha = int(PULSE_ALPHA * (1 - elapsed / PULSE_DURATION))
                overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                overlay.fill((*self.pulse_color, alpha))
                self.screen.blit(overlay, (0, 0))
            else:
                self.pulse_start = None

        # --- Red flash when hit ---
        if self.player.hit_flash:
            elapsed = pygame.time.get_ticks() - self.player.hit_time
            if elapsed < HIT_FLASH_DURATION:
                alpha = int(150 * (1 - elapsed / HIT_FLASH_DURATION))
                overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                overlay.fill((255, 0, 0, alpha))
                self.screen.blit(overlay, (0, 0))

        # --- Death fade + progressive blocky grayscale + ripple ---
        if self.player.dead:
            elapsed = pygame.time.get_ticks() - self.death_fade_start
            progress = min(1, elapsed / DEATH_FADE_DURATION)

            block_size = 16
            # Determine how far the grayscale wave has reached
            max_wave_radius = math.hypot(self.window_width, self.window_height) / 2
            current_wave_radius = progress * max_wave_radius
            center_x, center_y = self.window_width // 2, self.window_height // 2

            for y in range(0, self.window_height, block_size):
                for x in range(0, self.window_width, block_size):
                    # distance from center to block
                    dist = math.hypot(x - center_x, y - center_y)
                    if dist <= current_wave_radius:
                        color = self.screen.get_at((x, y))
                        gray = int(0.3 * color.r + 0.59 * color.g + 0.11 * color.b)
                        r = int(color.r * (1 - progress) + gray * progress)
                        g = int(color.g * (1 - progress) + gray * progress)
                        b = int(color.b * (1 - progress) + gray * progress)
                        pygame.draw.rect(self.screen, (r, g, b),
                                        pygame.Rect(x, y, block_size, block_size))

            # Ripple effect
            ripple_progress = progress
            for i in range(RIPPLE_WAVES):
                radius = int(ripple_progress * (self.window_width + self.window_height) / 3 + i * 20)
                ripple_alpha = max(0, 150 - i * 30)
                ripple_color = (*self.border_color, ripple_alpha)
                ripple_surface = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
                pygame.draw.circle(ripple_surface, ripple_color, (center_x, center_y), radius, 4)
                self.screen.blit(ripple_surface, (0, 0))

            # Black fade overlay
            fade_alpha = min(255, int(255 * progress))
            overlay = pygame.Surface((self.window_width, self.window_height))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(fade_alpha)
            self.screen.blit(overlay, (0, 0))

            if elapsed >= DEATH_FADE_DURATION:
                self.show_retry = True
                self.show_menu_button = True
                self.draw_undertale_death_menu()


        pygame.display.flip()

# -------------------------- RUN --------------------------

if __name__ == "__main__":
    Game().run()
