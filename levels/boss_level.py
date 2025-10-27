import sys
import os
import pygame
import random
import math

# Add the parent directory of spiritbound_title.py to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import spiritbound_title
import spiritbound_game

# --- Constants ---
WIDTH, HEIGHT = 800, 600
FPS = 60
PLAYER_SIZE = 30
PLAYER_SPEED = 250
DASH_SPEED = 1500
DASH_FRAMES = 3
DASH_COOLDOWN = 400
AFTERIMAGE_LIFETIME = 250

HOMING_MISSILE_LIFETIME = 2
HOMING_MISSILE_SPEED = 100
HOMING_MISSILE_ACCELERATION = 120

HIT_FLASH_DURATION = 150
HIT_SHAKE_INTENSITY = 5

DEATH_FADE_DURATION = 1000

BG_FLASH_DURATION = 500
ATTACK_TRANSITION_SPEED = 300
ATTACK_DURATION = 2000
SPECIAL_ATTACKS_TO_VULNERABLE = 4

PLAYER_ATTACK_COOLDOWN = 400
PLAYER_SWORD_LENGTH = 50
PLAYER_SWORD_HIT_RADIUS = 20
SWORD_DAMAGE = 10
SWORD_TRAIL_LIFETIME = 150

ATTACK_TEXT_SPEED_IN = 1500  # pixels/sec, entering speed
ATTACK_TEXT_SLOW_DURATION = 500  # ms to stay at center
ATTACK_TEXT_SPEED_OUT = 1500  # pixels/sec, exiting speed

SPIRIT_BOMB_MAX_SCALE = 2.0
SPIRIT_BOMB_MIN_SCALE = 0.4
SPIRIT_BOMB_GROW_SPEED = 0.4  # scale units per second
SPIRIT_BOMB_CLICKS_TO_DEFUSE = 5
SPIRIT_BOMB_SHRINK_DURATION = 2
SPIRIT_BOMB_TOTAL_DURATION = 1500

BOSS_MAX_HEALTH = 1500

VICTORY_EFFECT_DURATION = 5000  # milliseconds
CONFETTI_COUNT = 100
CONFETTI_COLORS = [
    (255, 50, 50),
    (50, 255, 50),
    (50, 50, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255)
]

class ConfettiParticle:
    def __init__(self):
        self.pos = pygame.Vector2(random.randint(0, WIDTH), random.randint(-HEIGHT, 0))
        self.vel = pygame.Vector2(random.uniform(-50, 50), random.uniform(100, 300))
        self.color = random.choice(CONFETTI_COLORS)
        self.size = random.randint(4, 8)
        self.life = random.uniform(2, 5)  # seconds

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.pos.x, self.pos.y, self.size, self.size))


class AfterImage:
    def __init__(self, pos, order, total):
        self.pos = pos
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
    def __init__(self, start, end):
        self.start = pygame.Vector2(start)
        self.end = pygame.Vector2(end)
        self.created_at = pygame.time.get_ticks()

    def get_alpha(self):
        elapsed = pygame.time.get_ticks() - self.created_at
        if elapsed > SWORD_TRAIL_LIFETIME:
            return 0
        return int(255 * (1 - elapsed / SWORD_TRAIL_LIFETIME))

    def draw(self, screen):
        alpha = self.get_alpha()
        if alpha <= 0:
            return
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(surf, (255, 255, 255, alpha), self.start, self.end, 6)  # thick white line
        screen.blit(surf, (0, 0))


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PLAYER_SIZE, PLAYER_SIZE)
        self.speed = PLAYER_SPEED
        self.health = 100
        self.dashing = False
        self.dash_dir = pygame.Vector2(0, 0)
        self.dash_progress = 0
        self.last_dash = -DASH_COOLDOWN
        self.dash_key_pressed = False
        self.afterimages = []
        self.facing = pygame.Vector2(0, 1)
        self.hit_flash = False
        self.hit_time = 0
        self.sword_trails = []
        self.can_attack = True
        self.dead = False
        self.attacking = False
        self.attack_duration = 200  # milliseconds the sword attack lasts
        self.attack_start_time = 0
        self.last_attack_time = -PLAYER_ATTACK_COOLDOWN  # allow immediate first attack



    def start_dash(self):
        self.dashing = True
        self.dash_dir = self.facing.copy()
        self.dash_progress = 0

    def take_damage(self, amount):
        if self.dead:
            return
        self.health = max(0, self.health - amount)
        self.hit_flash = True
        self.hit_time = pygame.time.get_ticks()
        if self.health <= 0:
            self.dead = True

    def attack(self, target_pos, boss):
        now = pygame.time.get_ticks()
        if self.dead or self.attacking or (now - self.last_attack_time < PLAYER_ATTACK_COOLDOWN):
            return
        self.can_attack = False
        self.attacking = True
        self.attack_start_time = now
        self.last_attack_time = now

        self.attack_start_time = pygame.time.get_ticks()

        center = pygame.Vector2(self.rect.center)
        direction = (pygame.Vector2(target_pos) - center).normalize()
        tip = center + direction * PLAYER_SWORD_LENGTH

        self.sword_trails.append(SwordTrail(center, tip))

        # Damage boss if in range of tip
        bx, by = boss.rect.center
        if math.hypot(bx - tip.x, by - tip.y) <= PLAYER_SWORD_HIT_RADIUS + boss.rect.width / 2:
            boss.take_damage(SWORD_DAMAGE)


    def release_attack(self):
        self.can_attack = True

    def update(self, keys, dt):
        if self.dead:
            return
        now = pygame.time.get_ticks()

        # --- Sword attack handling ---
        if self.attacking:
            elapsed = now - self.attack_start_time
            if elapsed <= self.attack_duration:
                center = pygame.Vector2(self.rect.center)
                mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
                direction = (mouse_pos - center).normalize()
                tip = center + direction * PLAYER_SWORD_LENGTH
                self.sword_trails.append(SwordTrail(center, tip))
            else:
                self.attacking = False
                self.can_attack = True

        # --- Dash handling ---
        if keys[pygame.K_LSHIFT]:
            if not self.dash_key_pressed and now - self.last_dash >= DASH_COOLDOWN:
                self.start_dash()
            self.dash_key_pressed = True
        else:
            self.dash_key_pressed = False

        dx = dy = 0
        if not self.dashing:
            # Prevent diagonal movement: prioritize vertical over horizontal
            if keys[pygame.K_w]:
                dy = -self.speed * dt
                self.facing = pygame.Vector2(0, -1)
            elif keys[pygame.K_s]:
                dy = self.speed * dt
                self.facing = pygame.Vector2(0, 1)
            elif keys[pygame.K_a]:
                dx = -self.speed * dt
                self.facing = pygame.Vector2(-1, 0)
            elif keys[pygame.K_d]:
                dx = self.speed * dt
                self.facing = pygame.Vector2(1, 0)

            self.rect.x += dx
            self.rect.y += dy
        else:
            # Dash movement
            self.rect.x += self.dash_dir.x * DASH_SPEED * dt
            self.rect.y += self.dash_dir.y * DASH_SPEED * dt
            self.dash_progress += 1
            self.afterimages.append(AfterImage(self.rect.center, self.dash_progress, DASH_FRAMES))
            if self.dash_progress >= DASH_FRAMES:
                self.dashing = False
                self.last_dash = now

        # Keep player inside screen bounds
        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

    def draw(self, screen):
        for ai in self.afterimages[:]:
            alpha = ai.get_alpha()
            if alpha <= 0:
                self.afterimages.remove(ai)
                continue
            surf = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
            surf.fill((255, 255, 255, alpha))
            screen.blit(surf, (ai.pos[0] - PLAYER_SIZE // 2, ai.pos[1] - PLAYER_SIZE // 2))

        for trail in self.sword_trails[:]:
            alpha = trail.get_alpha()
            if alpha <= 0:
                self.sword_trails.remove(trail)
                continue
            trail.draw(screen)

        color = (128, 128, 128) if self.dead else (255, 255, 255)
        pos = self.rect.topleft
        if self.hit_flash:
            elapsed = pygame.time.get_ticks() - self.hit_time
            if elapsed < HIT_FLASH_DURATION:
                color = (255, 255, 255)
                offset_x = random.randint(-HIT_SHAKE_INTENSITY, HIT_SHAKE_INTENSITY)
                offset_y = random.randint(-HIT_SHAKE_INTENSITY, HIT_SHAKE_INTENSITY)
                pos = (self.rect.x + offset_x, self.rect.y + offset_y)
            else:
                self.hit_flash = False
        pygame.draw.rect(screen, color, (*pos, PLAYER_SIZE, PLAYER_SIZE))


class HomingMissile:
    def __init__(self, pos, target):
        self.pos = pygame.Vector2(pos)
        self.rect = pygame.Rect(pos[0], pos[1], 20, 20)
        self.target = target
        self.speed = HOMING_MISSILE_SPEED
        self.acceleration = HOMING_MISSILE_ACCELERATION
        self.life_time = HOMING_MISSILE_LIFETIME
        self.spawn_time = pygame.time.get_ticks() / 1000

    def update(self, dt):
        direction = pygame.Vector2(self.target.rect.center) - self.pos
        if direction.length() > 0:
            direction = direction.normalize()
            self.pos += direction * (self.speed * dt)
            self.speed += self.acceleration * dt
            self.rect.center = self.pos

    def is_dead(self):
        return (pygame.time.get_ticks() / 1000 - self.spawn_time) > self.life_time

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 100, 0), self.rect)


class Boss:
    def __init__(self, x, y, max_health=300):
        self.rect = pygame.Rect(x, y, 150, 150)
        self.max_health = max_health      # Constant max health
        self.health = max_health          # Current health
        self.attack_patterns = ["rain", "burst", "sides", "rising", "homing", "spirit_bomb"]
        self.active_attacks = []
        self.special_attack_counter = 0
        self.vulnerable = False           # Never start vulnerable
        self.vulnerability_start = None
        self.vulnerability_duration = 5000
        self.warning_issued = False
        self.hit_flash = False
        self.hit_time = 0

    def take_damage(self, amount):
        if self.vulnerable:
            self.health -= amount
            self.hit_flash = True
            self.hit_time = pygame.time.get_ticks()

    def spawn_attack(self, pattern, player):
        if self.vulnerable:
            return
        self.active_attacks.clear()
        shapes = []

        if pattern == "rain":
            for _ in range(15):
                x = random.randint(50, WIDTH - 50)
                shapes.append({
                    "type": "rain",
                    "rect": pygame.Rect(x, 0, 20, 20),
                    "vel": pygame.Vector2(random.uniform(-100, 100), random.uniform(400, 600))
                })

        elif pattern == "rising":
            for _ in range(15):
                x = random.randint(50, WIDTH - 50)
                shapes.append({
                    "type": "rising",
                    "rect": pygame.Rect(x, HEIGHT, 20, 20),
                    "vel": pygame.Vector2(random.uniform(-100, 100), -random.uniform(400, 600))
                })

        elif pattern == "sides":
            for _ in range(10):
                y = random.randint(50, HEIGHT - 50)
                direction = random.choice(["left", "right"])
                x = 0 if direction == "left" else WIDTH
                vx = random.uniform(500, 700) * (1 if direction == "left" else -1)
                shapes.append({
                    "type": "sides",
                    "rect": pygame.Rect(x, y, 30, 30),
                    "vel": pygame.Vector2(vx, 0)
                })

        elif pattern == "burst":
            cx, cy = self.rect.center
            for i in range(20):
                angle = math.radians(i * 18)
                vx = math.cos(angle) * random.uniform(400, 600)
                vy = math.sin(angle) * random.uniform(400, 600)
                shapes.append({
                    "type": "burst",
                    "rect": pygame.Rect(cx, cy, 15, 15),
                    "vel": pygame.Vector2(vx, vy)
                })

        elif pattern == "homing":
            missile = HomingMissile(self.rect.center, player)
            shapes.append({"type": "homing", "obj": missile})

        elif pattern == "spirit_bomb":
            bomb_rect = pygame.Rect(
                random.randint(150, WIDTH - 150),
                random.randint(150, HEIGHT - 150),
                60, 60
            )
            bomb = {
                "type": "spirit_bomb",
                "rect": bomb_rect,
                "solved": False,
                "spawn_time": pygame.time.get_ticks(),
                "scale": 1.0,
                "explode_time": SPIRIT_BOMB_SHRINK_DURATION,
                "puzzle_progress": 0,  # track clicks
                "flash_timer": 0       # for visual flash on click
            }
            shapes.append(bomb)

        self.active_attacks.extend(shapes)
        self.special_attack_counter += 1

        if self.special_attack_counter >= SPECIAL_ATTACKS_TO_VULNERABLE:
            self.vulnerable = True
            self.vulnerability_start = pygame.time.get_ticks()
            self.warning_issued = False
            self.special_attack_counter = 0

    def update_attacks(self, player, dt):
        now = pygame.time.get_ticks()
        for attack in self.active_attacks[:]:
            # --- SPIRIT BOMB ---
            if attack["type"] == "spirit_bomb":
                elapsed = now - attack["spawn_time"]
                shrink_ratio = min(1.0, elapsed / SPIRIT_BOMB_SHRINK_DURATION)
                attack["scale"] = 1.0 - shrink_ratio * 0.8

                # Player clicks / disarms
                mouse_pos = pygame.mouse.get_pos()
                mouse_pressed = pygame.mouse.get_pressed()
                if not attack["solved"] and mouse_pressed[0] and attack["rect"].collidepoint(mouse_pos):
                    attack["puzzle_progress"] += 1
                    attack["flash_timer"] = 100
                    if attack["puzzle_progress"] >= 3:
                        attack["solved"] = True
                        self.active_attacks.remove(attack)
                        continue

                # Time up → explosion
                if elapsed >= attack["explode_time"] and not attack["solved"]:
                    dx = player.rect.centerx - attack["rect"].centerx
                    dy = player.rect.centery - attack["rect"].centery
                    dist = math.hypot(dx, dy)
                    if dist < 250:
                        player.take_damage(100)
                    self.active_attacks.remove(attack)
                    continue

            # --- HOMING MISSILES ---
            if attack["type"] == "homing":
                obj = attack["obj"]
                obj.update(dt)
                if obj.rect.colliderect(player.rect):
                    player.take_damage(20)
                    self.active_attacks.remove(attack)
                    continue
                elif obj.is_dead():
                    self.active_attacks.remove(attack)
                    continue

            # --- NORMAL SHAPES ---
            if "vel" in attack:
                attack["rect"].x += attack["vel"].x * dt
                attack["rect"].y += attack["vel"].y * dt
                if attack["rect"].colliderect(player.rect):
                    player.take_damage(10)
                    self.active_attacks.remove(attack)
                    continue
                if (attack["rect"].top > HEIGHT or attack["rect"].bottom < 0 or
                    attack["rect"].right < 0 or attack["rect"].left > WIDTH):
                    self.active_attacks.remove(attack)
                    continue

    def draw(self, screen):
        # Draw boss
        color = (255, 0, 0)
        if self.vulnerable:
            color = (255, 100, 100)
        if self.hit_flash:
            elapsed = pygame.time.get_ticks() - self.hit_time
            if elapsed < HIT_FLASH_DURATION:
                color = (255, 255, 255)
            else:
                self.hit_flash = False
        pygame.draw.rect(screen, color, self.rect)

        # Draw attacks
        for attack in self.active_attacks:
            rect = attack.get("rect")
            if not rect:
                continue
            if attack["type"] == "homing":
                attack["obj"].draw(screen)
            elif attack["type"] == "spirit_bomb":
                surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                intensity = int(255 * attack.get("scale", 1.0))
                pygame.draw.circle(surf, (255, intensity, 0, 200), (rect.width // 2, rect.height // 2), int(rect.width * attack.get("scale", 1.0) // 2))
                screen.blit(surf, rect.topleft)
            elif "vel" in attack:
                pygame.draw.rect(screen, (255, 255, 0), rect)


class Shockwave:
    def __init__(self, center, max_radius=WIDTH, speed=1200):
        self.center = pygame.Vector2(center)
        self.radius = 0
        self.max_radius = max_radius
        self.speed = speed
        self.finished = False

    def update(self, dt):
        self.radius += self.speed * dt
        if self.radius >= self.max_radius:
            self.finished = True

    def draw(self, screen):
        if self.radius > 0:
            alpha = max(50, 150 - int(100 * (self.radius / self.max_radius)))
            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 200, 50, alpha), self.center, int(self.radius), width=8)
            screen.blit(surf, (0, 0))


class BossLevel:
    ATTACK_FLASH_COLORS = {
        "rain": (0, 255, 0),
        "rising": (0, 0, 255),
        "sides": (255, 0, 255),
        "burst": (255, 255, 0),
        "homing": (255, 100, 0),
        "spirit_bomb": (255, 0, 255)
    }

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Boss Battle")
        self.clock = pygame.time.Clock()
        self.player = Player(WIDTH // 2, HEIGHT // 2)  # fixed initialization
        self.boss = Boss(WIDTH // 2 - 75, 50)
        self.shockwaves = []
        self.bg_color = pygame.Color(0, 0, 0)
        self.flash_start_time = None
        self.flash_color = pygame.Color(0, 0, 0)
        self.attack_start_time = None
        self.attack_in_progress = False
        self.current_pattern = None
        self.attack_text_state = None
        self.attack_text_pos = pygame.Vector2(WIDTH + 100, HEIGHT // 2)
        self.attack_text_timer = 0
        self.player_flash_start = None
        self.player_flash_color = pygame.Color(255, 0, 0)
        self.show_retry = False
        self.death_fade_start = None
        self.boss_health_y = -25 
        self.show_victory = False
        self.victory_start_time = None
        self.victory_confetti = []
        self.victory_bg_color = pygame.Color(0, 0, 0)

        # --- MUSIC SETUP ---
        try:
            pygame.mixer.init()
            parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            self.bgm_path = os.path.join(parent_dir, "assets", "spiritbound_boss_music.wav")
            pygame.mixer.music.load(self.bgm_path)
            pygame.mixer.music.play(loops=-1)  # loop indefinitely
        except Exception as e:
            print(f"Error loading music: {e}")

    def handle_retry_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.mixer.music.stop()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.player.attack(pygame.mouse.get_pos(), self.boss)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.player.release_attack()
            elif event.type == pygame.KEYDOWN and self.show_retry:
                if event.key == pygame.K_r:
                    self.respawn_player()
                    self.show_retry = False
                elif event.key == pygame.K_m:
                    try:
                        pygame.mixer.music.stop()  # stop music immediately
                        pygame.display.quit()
                        spiritbound_title.main_menu()
                    except Exception:
                        pygame.quit()
                        sys.exit()
                    return
            elif event.type == pygame.KEYDOWN and self.show_victory:
                if event.key == pygame.K_m:
                    try:
                        pygame.mixer.music.stop()
                        pygame.display.quit()
                        spiritbound_title.main_menu()
                    except Exception:
                        pygame.quit()
                        sys.exit()
                    return

    def draw_victory_screen(self):
        font = pygame.font.SysFont(None, 72)
        small_font = pygame.font.SysFont(None, 36)
        title = font.render("VICTORY!", True, (50, 220, 50))
        opt1 = small_font.render("[M] Menu", True, (255, 255, 255))
        cx, cy = WIDTH // 2, HEIGHT // 2
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 100))
        self.screen.blit(opt1, (cx - opt1.get_width() // 2, cy))

    def draw(self):
        if self.show_victory:
            elapsed = pygame.time.get_ticks() - self.victory_start_time
            t = elapsed / 50
            r = int((math.sin(t) * 0.5 + 0.5) * 255)
            g = int((math.sin(t + 2) * 0.5 + 0.5) * 255)
            b = int((math.sin(t + 4) * 0.5 + 0.5) * 255)
            self.victory_bg_color = pygame.Color(r, g, b)
            self.screen.fill(self.victory_bg_color)

            if elapsed < VICTORY_EFFECT_DURATION:
                for conf in self.victory_confetti[:]:
                    conf.update(self.clock.get_time() / 1000)
                    conf.draw(self.screen)
                    if conf.life <= 0 or conf.pos.y > HEIGHT:
                        self.victory_confetti.remove(conf)
                
            else:
                self.victory_confetti.clear()

            self.draw_victory_screen()
            return
        
        self.screen.fill(self.bg_color)

        # --- ddDraw Boss ---
        boss_color = (255, 150, 255) if self.boss.hit_flash and (
            pygame.time.get_ticks() - self.boss.hit_time) < HIT_FLASH_DURATION else (10, 10, 100)
        pygame.draw.rect(self.screen, boss_color, self.boss.rect)

        # --- Draw Boss Attacks ---
        for atk in self.boss.active_attacks:
            # Homing missiles are always drawn
            if atk.get("type") == "homing":
                atk["obj"].draw(self.screen)
                continue

            # Hide other attacks while boss is vulnerable
            if self.boss.vulnerable:
                continue

            rect = atk.get("rect")
            if not rect:
                continue

            # Spirit Bomb
            if "solved" in atk:
                scale = atk.get("scale", 1.0)
                exploded = atk.get("exploded", False)
                radius = atk.get("explosion_radius", 0)

                if exploded:
                    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (255, 80, 0, 150), rect.center, int(radius))
                    self.screen.blit(surf, (0, 0))
                else:
                    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    color = atk.get("color", (255, 255, 0))
                    offset = atk.get("distort_offset", (0, 0))
                    pygame.draw.circle(
                        surf,
                        (*color, 200),
                        (rect.width // 2 + offset[0], rect.height // 2 + offset[1]),
                        int(rect.width * scale // 2)
                    )
                    self.screen.blit(surf, rect.topleft)

                    # Draw text if not solved yet
                    if not atk["solved"]:
                        font = pygame.font.SysFont(None, 24)
                        text_surf = font.render("CLICK TO DEFUSE", True, (255, 255, 255))
                        text_rect = text_surf.get_rect(center=(rect.centerx, rect.top - 20))
                        self.screen.blit(text_surf, text_rect)

            # Normal attack rectangles
            elif "vel" in atk:
                pygame.draw.rect(self.screen, (255, 60, 60), rect)

        # --- Draw Shockwaves ---
        for sw in self.shockwaves:
            sw.draw(self.screen)

        # --- Draw Player ---
        self.player.draw(self.screen)

        # --- Player Health Bar ---
        bar_width = 200
        bar_height = 20
        x = 10
        y = HEIGHT - bar_height - 10
        pygame.draw.rect(self.screen, (255, 0, 0), (x, y, bar_width, bar_height))
        pygame.draw.rect(self.screen, (0, 255, 0),
                         (x, y, bar_width * (self.player.health / 100), bar_height))

        # --- Boss Health Bar (only if vulnerable) ---
        if self.boss.vulnerable:
            target_y = 10
            dt = self.clock.get_time() / 1000
            self.boss_health_y += 300 * dt
            if self.boss_health_y > target_y:
                self.boss_health_y = target_y

            boss_bar_width = 300
            boss_bar_height = 25
            bx = WIDTH // 2 - boss_bar_width // 2
            by = int(self.boss_health_y)
            pygame.draw.rect(self.screen, (255, 0, 0), (bx, by, boss_bar_width, boss_bar_height))
            pygame.draw.rect(
                self.screen,
                (0, 255, 0),
                (bx, by, boss_bar_width * (self.boss.health / self.boss.max_health), boss_bar_height)
            )

        # --- Player Damage Flash Overlay ---
        if self.player_flash_start:
            elapsed = pygame.time.get_ticks() - self.player_flash_start
            if elapsed < HIT_FLASH_DURATION:
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.fill(self.player_flash_color)
                alpha = int(150 * (1 - elapsed / HIT_FLASH_DURATION))
                overlay.set_alpha(alpha)
                self.screen.blit(overlay, (0, 0))
            else:
                self.player_flash_start = None

        # --- Death Fade Overlay ---
        if self.player.dead and self.death_fade_start:
            elapsed = pygame.time.get_ticks() - self.death_fade_start
            progress = min(1.0, elapsed / DEATH_FADE_DURATION)
            fade_alpha = int(255 * progress)
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(fade_alpha)
            self.screen.blit(overlay, (0, 0))

        # --- Retry Menu Display ---
        if self.show_retry:
            font = pygame.font.SysFont(None, 72)
            small_font = pygame.font.SysFont(None, 36)
            title = font.render("YOU DIED", True, (220, 40, 40))
            opt1 = small_font.render("[R] Respawn", True, (255, 255, 255))
            opt2 = small_font.render("[M] Menu", True, (200, 200, 200))
            cx, cy = WIDTH // 2, HEIGHT // 2
            self.screen.blit(title, (cx - title.get_width() // 2, cy - 100))
            self.screen.blit(opt1, (cx - opt1.get_width() // 2, cy))
            self.screen.blit(opt2, (cx - opt2.get_width() // 2, cy + 48))

        # --- Draw Attack Text ---
        if self.boss.vulnerable and self.attack_text_state:
            font = pygame.font.SysFont(None, 72)
            text_surf = font.render("ATTACK!", True, (255, 50, 50))
            self.screen.blit(
                text_surf,
                (self.attack_text_pos.x - text_surf.get_width() // 2,
                 self.attack_text_pos.y - text_surf.get_height() // 2)
            )

    def respawn_player(self):
        self.player.health = 100
        self.player.dead = False
        self.player.rect.center = (WIDTH // 2, HEIGHT - 80)
        self.player.afterimages.clear()
        self.player.sword_trails.clear()
        self.player.can_attack = True
        self.death_fade_start = None
        self.player.hit_flash = False
        self.player_flash_start = None

        self.boss.health = 300
        self.boss.active_attacks.clear()
        self.boss.vulnerable = False
        self.boss.warning_issued = False
        self.boss.special_attack_counter = 0
        self.boss.vulnerability_start = None
        self.boss_health_y = -25
        self.boss.health = self.boss.max_health


        self.shockwaves.clear()
        self.attack_in_progress = False
        self.attack_text_state = None
        self.attack_text_pos = pygame.Vector2(WIDTH + 100, HEIGHT // 2)
        if hasattr(self, "vuln_text_triggered"):
            del self.vuln_text_triggered

    # --- Run game loop ---
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000
            keys = pygame.key.get_pressed()

            self.handle_retry_events()

            # --- Only update game if not in retry or victory ---
            if not self.show_retry and not self.show_victory:
                self.update_bg_flash()
                self.player.update(keys, dt)
                self.update_attacks(dt)

                if self.player.dead:
                    if not self.death_fade_start:
                        self.death_fade_start = pygame.time.get_ticks()
                    elif pygame.time.get_ticks() - self.death_fade_start > DEATH_FADE_DURATION:
                        self.show_retry = True

            # --- Check boss defeat ---
            if self.boss.health <= 0 and not self.show_victory:
                self.show_victory = True
                # Trigger victory flash
                self.flash_start_time = pygame.time.get_ticks()
                self.flash_color = pygame.Color(255, 255, 255)  # Bright flash
                self.victory_flash_done = False  # Track flash completion
                self.victory_start_time = pygame.time.get_ticks()
                self.victory_confetti = [ConfettiParticle() for _ in range(CONFETTI_COUNT)]

            # --- Draw everything ---
            self.draw()
            pygame.display.flip()

            # --- Victory flash handling ---
            if self.show_victory and not getattr(self, "victory_flash_done", True):
                elapsed = pygame.time.get_ticks() - self.flash_start_time
                if elapsed >= BG_FLASH_DURATION:
                    self.victory_flash_done = True

    # --- Background flash ---
    def update_bg_flash(self):
        if self.flash_start_time:
            elapsed = pygame.time.get_ticks() - self.flash_start_time
            if elapsed < BG_FLASH_DURATION:
                fade = 1 - elapsed / BG_FLASH_DURATION
                self.bg_color.r = int(self.flash_color.r * fade)
                self.bg_color.g = int(self.flash_color.g * fade)
                self.bg_color.b = int(self.flash_color.b * fade)
            else:
                self.flash_start_time = None
                self.bg_color = pygame.Color(0, 0, 0)

    # --- Attack text animation ---
    def update_attack_text(self, dt):
        if not self.attack_text_state:
            return

        now = pygame.time.get_ticks()
        target_x = WIDTH // 2

        if self.attack_text_state == "in":
            self.attack_text_pos.x -= ATTACK_TEXT_SPEED_IN * dt
            if self.attack_text_pos.x <= target_x:
                self.attack_text_pos.x = target_x
                self.attack_text_state = "slow"
                self.attack_text_timer = now
        elif self.attack_text_state == "slow":
            if now - self.attack_text_timer >= ATTACK_TEXT_SLOW_DURATION:
                self.attack_text_state = "out"
        elif self.attack_text_state == "out":
            self.attack_text_pos.x += ATTACK_TEXT_SPEED_OUT * dt
            if self.attack_text_pos.x > WIDTH + 100:
                self.attack_text_state = None


    # --- Update attacks (with working Spirit Bomb) ---
    def update_attacks(self, dt):
        now = pygame.time.get_ticks()

        # --- Handle boss vulnerability ---
        if self.boss.vulnerable:
            elapsed = now - self.boss.vulnerability_start
            if elapsed >= self.boss.vulnerability_duration - 1000 and not self.boss.warning_issued:
                self.flash_start_time = now
                self.flash_color = pygame.Color(255, 100, 0)
                self.boss.warning_issued = True
            if elapsed >= self.boss.vulnerability_duration:
                self.boss.vulnerable = False
                self.boss.warning_issued = False
                self.attack_in_progress = False
                if hasattr(self, "vuln_text_triggered"):
                    del self.vuln_text_triggered
                self.attack_text_state = None
                self.boss_health_y = -25
            if not hasattr(self, "vuln_text_triggered"):
                self.attack_text_pos = pygame.Vector2(WIDTH + 100, HEIGHT // 2)
                self.attack_text_state = "in"
                self.attack_text_timer = now
                self.vuln_text_triggered = True
            self.update_attack_text(dt)
            return

        # --- Normal attack cycle ---
        if not self.attack_in_progress or now - self.attack_start_time >= ATTACK_DURATION:
            pattern = random.choice(self.boss.attack_patterns)
            self.boss.spawn_attack(pattern, self.player)
            self.attack_start_time = now
            self.attack_in_progress = True
            self.current_pattern = pattern
            color = self.ATTACK_FLASH_COLORS.get(pattern, (255, 255, 255))
            self.flash_start_time = now
            self.flash_color = pygame.Color(*color)
            self.attack_text_pos = pygame.Vector2(WIDTH + 100, HEIGHT // 2)
            self.attack_text_state = "in"
            self.attack_text_timer = now

        # --- Update attack text ---
        if self.attack_text_state:
            self.update_attack_text(dt)

        # --- Update active attacks ---
        for atk in self.boss.active_attacks[:]:
            rect = atk.get("rect")
            if not rect and atk.get("type") != "homing":
                continue

            # Homing missiles
            if atk.get("type") == "homing":
                obj = atk["obj"]
                obj.update(dt)

                # Collision with player
                if obj.rect.colliderect(self.player.rect):
                    self.player.take_damage(20)
                    self.player_flash_start = pygame.time.get_ticks()
                    self.shockwaves.append(Shockwave(obj.pos))
                    self.boss.active_attacks.remove(atk)
                    continue

                # Remove if lifetime exceeded
                if obj.is_dead():
                    self.shockwaves.append(Shockwave(obj.pos))
                    self.boss.active_attacks.remove(atk)
                    continue

            # Spirit Bomb
            elif "solved" in atk:
                atk.setdefault("lifetime", SPIRIT_BOMB_TOTAL_DURATION)
                atk.setdefault("flash_timer", 0)
                atk.setdefault("exploded", False)
                atk.setdefault("puzzle_progress", 0)
                atk.setdefault("damage_done", False)
                atk.setdefault("scale", 1.0)
                atk.setdefault("explosion_radius", 0)
                atk.setdefault("explosion_max_radius", 400)
                atk.setdefault("explosion_expand_speed", 800)

                # Mouse click to defuse
                mouse_pos = pygame.mouse.get_pos()
                mouse_pressed = pygame.mouse.get_pressed()
                if not atk["solved"] and mouse_pressed[0] and rect.collidepoint(mouse_pos):
                    atk["puzzle_progress"] += 1
                    atk["flash_timer"] = 100
                    if atk["puzzle_progress"] >= 3:
                        atk["solved"] = True
                        atk["exploded"] = False
                        atk["lifetime"] = 0

                # Flash/scale effect
                if atk["flash_timer"] > 0:
                    atk["flash_timer"] -= dt * 1000
                    atk["scale"] = 1.2
                else:
                    atk["scale"] = 1.0

                # Countdown lifetime for auto-explosion
                if not atk["solved"]:
                    atk["lifetime"] -= dt * 1000
                    progress = 1 - max(0, atk["lifetime"] / SPIRIT_BOMB_TOTAL_DURATION)
                    atk["color"] = (255, int(255 * (1 - progress)), 0)
                    atk["distort_offset"] = (random.randint(-5, 5) * progress, random.randint(-5, 5) * progress)
                    if atk["lifetime"] <= 0 and not atk["exploded"]:
                        atk["exploded"] = True

                # Explosion animation & damage
                if atk["exploded"]:
                    atk["explosion_radius"] += atk["explosion_expand_speed"] * dt
                    dx = self.player.rect.centerx - rect.centerx
                    dy = self.player.rect.centery - rect.centery
                    dist = math.hypot(dx, dy)
                    if dist < atk["explosion_radius"] and not atk["damage_done"]:
                        self.player.take_damage(100)
                        atk["damage_done"] = True
                        self.player_flash_start = pygame.time.get_ticks()
                    if atk["explosion_radius"] >= atk["explosion_max_radius"]:
                        if atk in self.boss.active_attacks:
                            self.boss.active_attacks.remove(atk)

            # Normal attack movement
            elif "vel" in atk:
                atk["rect"].x += atk["vel"].x * dt
                atk["rect"].y += atk["vel"].y * dt
                if atk["rect"].colliderect(self.player.rect):
                    self.player.take_damage(10)
                    self.player_flash_start = pygame.time.get_ticks()
                    self.boss.active_attacks.remove(atk)
                elif not (0 <= atk["rect"].x <= WIDTH and 0 <= atk["rect"].y <= HEIGHT):
                    self.boss.active_attacks.remove(atk)

        # --- Update shockwaves ---
        for sw in self.shockwaves[:]:
            sw.update(dt)
            if sw.finished:
                self.shockwaves.remove(sw)


if __name__ == "__main__":
    BossLevel().run()