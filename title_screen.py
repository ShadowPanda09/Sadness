import pygame
import sys
import math
import random

pygame.init()


# --- Window Setup ---
WIDTH, HEIGHT = 640, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Spiritbound")

clock = pygame.time.Clock()
font_title = pygame.font.Font(None, 80)
font_menu_base = 40
font_credits = pygame.font.Font(None, 28)

# --- Load Graphics ---
background_img = pygame.image.load("LandscapeAtlas.png").convert()
background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))
tileset_img = pygame.image.load("LandscapeAtlasTransparent.png").convert_alpha()

# --- Colors ---
DARK_BG = (10, 20, 25)
TITLE_COLOR = (160, 255, 255)
WHITE = (255, 255, 255)

# --- Menu Setup ---
menu_options = ["Play", "Settings", "Credits", "Quit"]
selected_index = 0

# --- Particle System ---
NUM_PARTICLES = 40
particles = []
for _ in range(NUM_PARTICLES):
    particles.append({
        'x': random.uniform(0, WIDTH),
        'y': random.uniform(0, HEIGHT),
        'radius': random.uniform(2, 5),
        'speed': random.uniform(10, 50),
        'angle': random.uniform(0, 2 * math.pi)
    })


def get_dynamic_color(base_time, offset):
    r = int(128 + 127 * math.sin(base_time * 0.8 + offset))
    g = int(128 + 127 * math.sin(base_time * 0.9 + offset + 2))
    b = int(128 + 127 * math.sin(base_time * 1.1 + offset + 4))
    r = int(r * 0.5)
    g = int(g * 0.8 + 40)
    b = int(b * 1.0)
    return (r, g, b)


# --- Character Drawing ---
def draw_character(surface, x, y, facing_angle, swinging, swing_progress):
    color_body = (220, 240, 230)
    pygame.draw.circle(surface, color_body, (x, y - 25), 8)
    pygame.draw.rect(surface, color_body, (x - 5, y - 20, 10, 25))
    pygame.draw.line(surface, color_body, (x - 5, y + 5), (x - 8, y + 15), 3)
    pygame.draw.line(surface, color_body, (x + 5, y + 5), (x + 8, y + 15), 3)
    pygame.draw.line(surface, color_body, (x - 5, y - 10), (x - 15, y - 5), 3)
    pygame.draw.line(surface, color_body, (x + 5, y - 10), (x + 15, y - 5), 3)

    # Sword
    sword_length = 33
    angle = facing_angle
    if swinging:
        swing_arc = 1.6 * (swing_progress - 0.5)
        angle += swing_arc
    end_x = x + math.cos(angle) * sword_length
    end_y = y + math.sin(angle) * sword_length
    pygame.draw.line(surface, (180, 255, 220), (x, y - 10), (end_x, end_y), 5)


def draw_title(surface):
    title_surf = font_title.render("SPIRITBOUND", True, TITLE_COLOR)
    rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    surface.blit(title_surf, rect)


def draw_menu(surface, selected_idx, time_val):
    start_y = HEIGHT // 2
    spacing = 50
    for i, option in enumerate(menu_options):
        if i == selected_idx:
            font_menu = pygame.font.Font(None, font_menu_base + 12)
            color = WHITE
        else:
            font_menu = pygame.font.Font(None, font_menu_base)
            color = get_dynamic_color(time_val, i * 2.5)
        text = font_menu.render(option, True, color)
        rect = text.get_rect(center=(WIDTH // 2, start_y + i * spacing))
        surface.blit(text, rect)


def show_credits():
    showing = True
    t = 0
    while showing:
        t += 0.016
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_RETURN]:
                showing = False

        screen.fill(DARK_BG)
        for p in particles:
            color = get_dynamic_color(t, p['angle'])
            pygame.draw.circle(screen, color, (int(p['x']), int(p['y'])), int(p['radius']))

        lines = [
            "Spiritbound",
            "A pixel art adventure",
            "",
            "Created by: You",
            "Powered by Python + Pygame",
            "",
            "Press ESC or ENTER to return"
        ]
        for i, line in enumerate(lines):
            color = get_dynamic_color(t, i)
            text = font_credits.render(line, True, color)
            rect = text.get_rect(center=(WIDTH // 2, 100 + i * 40))
            screen.blit(text, rect)
        pygame.display.flip()
        clock.tick(60)


def update_particles(dt, time_val):
    for p in particles:
        p['y'] -= p['speed'] * dt
        p['x'] += math.sin(time_val + p['angle']) * 0.5
        if p['y'] < -10:
            p['y'] = HEIGHT + 10
            p['x'] = random.uniform(0, WIDTH)

TILE_SIZE = 32
CHUNK_SIZE = WIDTH, HEIGHT  # one chunk fits a screen

# --- Define object regions within the LandscapeAtlasTransparent.png ---
# Format: name: (x, y, w, h)
SCENERY_TILES = {
    "tree1": (0, 0, 32, 48),
    "tree2": (32, 0, 32, 48),
    "rock": (64, 16, 32, 32),
    "bush": (96, 16, 32, 32),
    "fence": (128, 16, 32, 32),
    "column": (160, 0, 32, 48),
}

# --- Define object regions within the LandscapeAtlasTransparent.png ---
# Format: name: (x, y, w, h)
SCENERY_TILES = {
    "tree1": (0, 0, 32, 48),
    "tree2": (32, 0, 32, 48),
    "rock": (64, 16, 32, 32),
    "bush": (96, 16, 32, 32),
    "fence": (128, 16, 32, 32),
    "column": (160, 0, 32, 48),
}

def generate_chunk(offset_x, offset_y):
    """Generate a chunk with varied scenery from the tileset."""
    objects = []
    num_objects = random.randint(15, 25)

    for _ in range(num_objects):
        kind = random.choice(list(SCENERY_TILES.keys()))
        tx, ty, tw, th = SCENERY_TILES[kind]
        ox = random.randint(50, WIDTH - 50)
        oy = random.randint(50, HEIGHT - 50)

        # Rectangle for collision (smaller than sprite if it's tall)
        if "tree" in kind or "column" in kind:
            hit_h = 20  # only base collides
            rect = pygame.Rect(offset_x + ox, offset_y + oy + th - hit_h, tw, hit_h)
        else:
            rect = pygame.Rect(offset_x + ox, offset_y + oy, tw, th)

        objects.append({
            "kind": kind,
            "rect": rect,
            "sprite_rect": pygame.Rect(tx, ty, tw, th),
            "pos": (offset_x + ox, offset_y + oy),
        })

    return objects

# --- Game Loop ---
def play_game():
    player_x, player_y = 0, 0
    player_speed = 130
    facing_angle = 0
    swinging = False
    swing_timer = 0.0
    swing_duration = 0.45
    swing_cooldown = 0.6
    cooldown_timer = 0.0
    sword_length = 33
    score = 0

    # world generation
    chunk_map = {}  # stores chunks keyed by (cx, cy)
    current_chunk = (0, 0)
    chunk_map[current_chunk] = generate_chunk(0, 0)
    safe_radius = 150

    enemies = []
    while len(enemies) < 5:
        ex, ey = random.randint(-WIDTH//2, WIDTH//2), random.randint(-HEIGHT//2, HEIGHT//2)
        if math.hypot(ex, ey) > safe_radius:
            enemies.append({'x': ex, 'y': ey, 'speed': random.randint(70, 110)})

    sword_trail = []
    playing = True

    while playing:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                playing = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not swinging and cooldown_timer <= 0:
                    swinging = True
                    swing_timer = 0.0
                    cooldown_timer = swing_cooldown

        # movement
        keys = pygame.key.get_pressed()
        move_x = keys[pygame.K_d] - keys[pygame.K_a]
        move_y = keys[pygame.K_s] - keys[pygame.K_w]
        dx, dy = move_x * player_speed * dt, move_y * player_speed * dt

        new_x, new_y = player_x + dx, player_y + dy

        # Collision detection against static objects
        for chunk_coords, objects in chunk_map.items():
            for obj in objects:
                if obj['rect'].colliderect(pygame.Rect(new_x - 8, new_y - 8, 16, 16)):
                    dx, dy = 0, 0  # simple stop collision
        player_x += dx
        player_y += dy

        # Aim + swing timing
        mouse_x, mouse_y = pygame.mouse.get_pos()
        facing_angle = math.atan2(mouse_y - HEIGHT/2, mouse_x - WIDTH/2)

        if cooldown_timer > 0:
            cooldown_timer -= dt
        if swinging:
            swing_timer += dt
            if swing_timer > swing_duration:
                swinging = False

        swing_progress = swing_timer / swing_duration if swinging else 1.0
        swing_arc = 1.6 * (swing_progress - 0.5) if swinging else 0
        sword_angle = facing_angle + swing_arc
        sword_x = player_x + math.cos(sword_angle) * sword_length
        sword_y = player_y + math.sin(sword_angle) * sword_length

        sword_trail.append((sword_x, sword_y))
        if len(sword_trail) > 12:
            sword_trail.pop(0)

        # Enemy movement
        for e in enemies[:]:
            dx, dy = player_x - e['x'], player_y - e['y']
            dist = math.hypot(dx, dy)
            if dist != 0:
                e['x'] += e['speed'] * dt * dx / dist
                e['y'] += e['speed'] * dt * dy / dist
            if dist < 25:
                playing = False
            if swinging and math.hypot(e['x'] - sword_x, e['y'] - sword_y) < 25:
                enemies.remove(e)
                score += 1

        # Check chunk transitions
        new_chunk = (int(player_x // WIDTH), int(player_y // HEIGHT))
        if new_chunk != current_chunk:
            current_chunk = new_chunk
            if current_chunk not in chunk_map:
                offset_x, offset_y = current_chunk[0] * WIDTH, current_chunk[1] * HEIGHT
                chunk_map[current_chunk] = generate_chunk(offset_x, offset_y)

        # --- Drawing ---
        # Camera offset centers on player
        cam_x = player_x - WIDTH / 2
        cam_y = player_y - HEIGHT / 2

        # Draw visible chunks
        for (cx, cy), objects in chunk_map.items():
        # Draw base terrain
            screen.blit(background_img, (cx * WIDTH - cam_x, cy * HEIGHT - cam_y))

        # Sort by Y for proper depth ordering (trees behind player if above)
        for obj in sorted(objects, key=lambda o: o['pos'][1]):
            sx, sy = obj['pos']
            src = obj['sprite_rect']
            dest = (sx - cam_x, sy - cam_y)
            screen.blit(tileset_img, dest, src)

        # Sword trail
        if sword_trail:
            for i in range(1, len(sword_trail)):
                start = (sword_trail[i-1][0] - cam_x, sword_trail[i-1][1] - cam_y)
                end = (sword_trail[i][0] - cam_x, sword_trail[i][1] - cam_y)
                pygame.draw.line(screen, (200, 200, 200), start, end, 3)

        # Player & sword
        draw_character(screen, WIDTH//2, HEIGHT//2, facing_angle, swinging, swing_progress)

        # Enemies
        for e in enemies:
            pygame.draw.circle(screen, (220, 80, 80), (int(e['x'] - cam_x), int(e['y'] - cam_y)), 10)

        # HUD
        score_text = font_credits.render(f"Enemies slain: {score}", True, WHITE)
        hint_text = font_credits.render("Left-click to attack | ESC to return", True, (180, 180, 180))
        screen.blit(score_text, (10, 10))
        screen.blit(hint_text, (10, 35))

        pygame.display.flip()


# --- Main Menu Loop ---
time_val = 0
running = True
while running:
    dt = clock.tick(60) / 1000.0
    time_val += dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                selected_index = (selected_index - 1) % len(menu_options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                selected_index = (selected_index + 1) % len(menu_options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                choice = menu_options[selected_index]
                if choice == "Quit":
                    running = False
                elif choice == "Credits":
                    show_credits()
                elif choice == "Play":
                    play_game()
                elif choice == "Settings":
                    print("Settings menu not yet implemented.")

    screen.fill(DARK_BG)
    update_particles(dt, time_val)
    for p in particles:
        color = get_dynamic_color(time_val, p['angle'])
        pygame.draw.circle(screen, color, (int(p['x']), int(p['y'])), int(p['radius']))

    draw_title(screen)
    draw_character(screen, WIDTH // 2, HEIGHT // 2 - 50, 0, False, 0)
    draw_menu(screen, selected_index, time_val)
    pygame.display.flip()

pygame.quit()
sys.exit()
