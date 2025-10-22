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
font_menu_base = 40  # base font size for menu
font_credits = pygame.font.Font(None, 28)

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
        'angle': random.uniform(0, 2*math.pi)
    })

# --- Character Drawing Function ---
def draw_character(surface, x, y, time_val):
    aura_radius = 40 + int(5 * math.sin(time_val * 3))
    for i in range(3):
        radius = aura_radius - i * 8
        color_shift = int(40 * math.sin(time_val * 3 + i))
        aura_color = (
            max(0, min(255, 80 + color_shift)),
            max(0, min(255, 200 + color_shift)),
            max(0, min(255, 180 + color_shift))
        )
        pygame.draw.circle(surface, aura_color, (x, y), radius, 1)

    # Sword
    pygame.draw.rect(surface, (40, 100, 80), (x + 8, y - 40, 3, 25))
    pygame.draw.rect(surface, (140, 255, 200), (x + 7, y - 15, 5, 15))

    # Body (blank humanoid)
    color_body = (220, 240, 230)
    pygame.draw.circle(surface, color_body, (x, y - 25), 8)   # head
    pygame.draw.rect(surface, color_body, (x - 5, y - 20, 10, 25))  # torso
    pygame.draw.line(surface, color_body, (x - 5, y + 5), (x - 8, y + 15), 3)
    pygame.draw.line(surface, color_body, (x + 5, y + 5), (x + 8, y + 15), 3)
    pygame.draw.line(surface, color_body, (x - 5, y - 10), (x - 15, y - 5), 3)
    pygame.draw.line(surface, color_body, (x + 5, y - 10), (x + 15, y - 5), 3)

# --- Title Render ---
def draw_title(surface):
    title_surf = font_title.render("SPIRITBOUND", True, TITLE_COLOR)
    rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    surface.blit(title_surf, rect)

# --- Dynamic color modulation ---
def get_dynamic_color(base_time, offset):
    r = int(128 + 127 * math.sin(base_time * 0.8 + offset))
    g = int(128 + 127 * math.sin(base_time * 0.9 + offset + 2))
    b = int(128 + 127 * math.sin(base_time * 1.1 + offset + 4))
    r = int(r * 0.5)
    g = int(g * 0.8 + 40)
    b = int(b * 1.0)
    return (r, g, b)

# --- Menu Render with hover effect ---
def draw_menu(surface, selected_idx, time_val):
    start_y = HEIGHT // 2
    spacing = 50
    for i, option in enumerate(menu_options):
        if i == selected_idx:
            # Hover: bigger font + white color
            font_menu = pygame.font.Font(None, font_menu_base + 12)
            color = WHITE
        else:
            font_menu = pygame.font.Font(None, font_menu_base)
            color = get_dynamic_color(time_val, i * 2.5)
        text = font_menu.render(option, True, color)
        rect = text.get_rect(center=(WIDTH // 2, start_y + i * spacing))
        surface.blit(text, rect)

# --- Credits Screen ---
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

        # Animate background particles
        screen.fill(DARK_BG)
        for p in particles:
            color = get_dynamic_color(t, p['angle'])
            pygame.draw.circle(screen, color, (int(p['x']), int(p['y'])), int(p['radius']))
        # Draw credits text
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

# --- Animate background particles ---
def update_particles(dt, time_val):
    for p in particles:
        p['y'] -= p['speed'] * dt
        p['x'] += math.sin(time_val + p['angle']) * 0.5
        if p['y'] < -10:
            p['y'] = HEIGHT + 10
            p['x'] = random.uniform(0, WIDTH)

# --- Main Loop ---
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
                    print("Starting the game...")
                elif choice == "Settings":
                    print("Settings menu not yet implemented.")

    # --- Draw Scene ---
    screen.fill(DARK_BG)
    update_particles(dt, time_val)
    for p in particles:
        color = get_dynamic_color(time_val, p['angle'])
        pygame.draw.circle(screen, color, (int(p['x']), int(p['y'])), int(p['radius']))

    draw_title(screen)
    draw_character(screen, WIDTH // 2, HEIGHT // 2 - 50, time_val)
    draw_menu(screen, selected_index, time_val)

    pygame.display.flip()

pygame.quit()
sys.exit()
