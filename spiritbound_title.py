#All code in this file was made by AI
import pygame
import sys
import math
import random
import os
import spiritbound_game
from ffpyplayer.player import MediaPlayer

def play_video_overlay(filename, screen):
    """
    Play video on top of existing pygame screen.
    Stops background music while playing.
    """
    video_path = os.path.join(os.path.dirname(__file__), "assets", filename)

    # Pause background music
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()

    clock = pygame.time.Clock()
    player = MediaPlayer(video_path)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                player.close_player()

        frame, val = player.get_frame()
        if val == 'eof':
            break
        if frame is not None:
            image, pts = frame
            img_surface = pygame.image.frombuffer(
                image.to_bytearray()[0], image.get_size(), 'RGB'
            )
            img_surface = pygame.transform.scale(img_surface, screen.get_size())
            screen.blit(img_surface, (0, 0))
            pygame.display.flip()

        clock.tick(30)

    player.close_player()

    # Resume background music
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.unpause()
# -------------------------- Constants --------------------------
WIDTH, HEIGHT = 640, 480

DARK_BG = (10, 20, 25)
TITLE_COLOR = (160, 255, 255)
WHITE = (255, 255, 255)

MENU_OPTIONS = ["Play", "Settings", "Credits", "Quit"]
NUM_PARTICLES = 40

MUSIC_PATH = os.path.join(os.path.dirname(__file__), "assets", "menu title music.mp3")
MENU_LOOP_START = 0.0
GAME_LOOP_START = 25.0

TITLE_ANIM_START_TIME = 10
TITLE_ANIM_DURATION = 3

# -------------------------- Main Menu --------------------------
def main_menu():
    pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Spiritbound")
    clock = pygame.time.Clock()

    font_title = pygame.font.Font(None, 80)
    font_menu_base = 40
    font_credits = pygame.font.Font(None, 28)

    # ---------------- Particles ----------------
    particles = [{
        'x': random.uniform(0, WIDTH),
        'y': random.uniform(0, HEIGHT),
        'radius': random.uniform(2, 5),
        'speed': random.uniform(10, 50),
        'angle': random.uniform(0, 2 * math.pi)
    } for _ in range(NUM_PARTICLES)]

    # ---------------- Music ----------------
    pygame.mixer.music.load(MUSIC_PATH)
    MUSIC_LENGTH = pygame.mixer.Sound(MUSIC_PATH).get_length()
    HALF_TIME = MUSIC_LENGTH / 2
    pygame.mixer.music.play(-1, start=MENU_LOOP_START, fade_ms=2000)
    pygame.mixer.music.set_volume(0.5)

    flash_alpha = 255
    flash_surface = pygame.Surface((WIDTH, HEIGHT))
    flash_surface.fill((255, 255, 255))

    # ---------------- Helper Functions ----------------
    def update_particles(dt, time_val):
        for p in particles:
            p['y'] -= p['speed'] * dt
            p['x'] += math.sin(time_val + p['angle']) * 0.5
            if p['y'] < -10:
                p['y'] = HEIGHT + 10
                p['x'] = random.uniform(0, WIDTH)

    def get_dynamic_color(base_time, offset):
        r = int(128 + 127 * math.sin(base_time * 0.8 + offset)) * 0.5
        g = int(128 + 127 * math.sin(base_time * 0.9 + offset + 2)) * 0.8 + 40
        b = int(128 + 127 * math.sin(base_time * 1.1 + offset + 4)) * 1.0
        return (int(r), int(g), int(b))

    def draw_character_aura(surface, x, y, time_val, alpha=255):
        aura_radius = 40 + int(5 * math.sin(time_val * 3))
        for i in range(3):
            radius = aura_radius - i * 8
            shift = int(40 * math.sin(time_val * 3 + i))
            aura_color = (
                max(0, min(255, 80 + shift)),
                max(0, min(255, 200 + shift)),
                max(0, min(255, 180 + shift))
            )
            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(surf, aura_color + (alpha,), (x, y), radius, 1)
            surface.blit(surf, (0, 0))

    def draw_character(surface, x, y, time_val):
        draw_character_aura(surface, x, y, time_val)
        pygame.draw.rect(surface, (40, 100, 80), (x + 8, y - 40, 3, 25))
        pygame.draw.rect(surface, (140, 255, 200), (x + 7, y - 15, 5, 15))
        body_color = (220, 240, 230)
        pygame.draw.circle(surface, body_color, (x, y - 25), 8)
        pygame.draw.rect(surface, body_color, (x - 5, y - 20, 10, 25))
        pygame.draw.line(surface, body_color, (x - 5, y + 5), (x - 8, y + 15), 3)
        pygame.draw.line(surface, body_color, (x + 5, y + 5), (x + 8, y + 15), 3)
        pygame.draw.line(surface, body_color, (x - 5, y - 10), (x - 15, y - 5), 3)
        pygame.draw.line(surface, body_color, (x + 5, y - 10), (x + 15, y - 5), 3)

    def draw_title(surface):
        title_surf = font_title.render("SPIRITBOUND", True, TITLE_COLOR)
        rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 4))
        surface.blit(title_surf, rect)

    def draw_menu(surface, selected_idx, time_val):
        start_y = HEIGHT // 2
        spacing = 50
        for i, option in enumerate(MENU_OPTIONS):
            color = WHITE if i == selected_idx else get_dynamic_color(time_val, i * 2.5)
            font_menu = pygame.font.Font(None, font_menu_base + 12) if i == selected_idx else pygame.font.Font(None, font_menu_base)
            text = font_menu.render(option, True, color)
            rect = text.get_rect(center=(WIDTH // 2, start_y + i * spacing))
            surface.blit(text, rect)

    def show_credits():
        screen.fill(DARK_BG)
        credit_text = ["Credits", "MethodicGnat", "ShadowPanda09", "Present"]
        for i, line in enumerate(credit_text):
            surf = font_credits.render(line, True, WHITE)
            rect = surf.get_rect(center=(WIDTH//2, 100 + i*40))
            screen.blit(surf, rect)
        pygame.display.flip()
        pygame.time.delay(2000)

    # ---------------- Intro Sequence ----------------
    for text_str in ["MethodicGnat", "ShadowPanda09", "Present"]:
        intro_time, display_duration, fade_duration = 0, 1.5, 0.5
        while intro_time < display_duration:
            dt = clock.tick(60) / 1000.0
            intro_time += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
            screen.fill((0,0,0))
            fade_alpha = 255
            if intro_time < fade_duration:
                fade_alpha = int(255*(intro_time/fade_duration))
            elif intro_time > display_duration - fade_duration:
                fade_alpha = int(255*max(0, (display_duration-intro_time)/fade_duration))
            font_size = 60
            text_surf = pygame.font.Font(None, font_size).render(text_str, True, WHITE)
            text_surf.set_alpha(fade_alpha)
            rect = text_surf.get_rect(center=(WIDTH//2, HEIGHT//2))
            screen.blit(text_surf, rect)
            pygame.display.flip()

    # ---------------- Pre-Menu Animation ----------------
    menu_visible = False
    aura_time = 0
    title_anim_done = False
    title_anim_time = 0.0

    while not menu_visible:
        dt = clock.tick(60) / 1000.0
        aura_time += dt
        title_anim_time += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        t = min(1.0, aura_time/HALF_TIME)
        screen.fill((int(DARK_BG[0]*t), int(DARK_BG[1]*t), int(DARK_BG[2]*t)))
        draw_character_aura(screen, WIDTH//2, HEIGHT//2, pygame.time.get_ticks()/1000.0, alpha=int(255*t))

        if pygame.mixer.music.get_pos()/1000.0 >= TITLE_ANIM_START_TIME and not title_anim_done:
            progress = min(1.0, (title_anim_time - TITLE_ANIM_START_TIME)/TITLE_ANIM_DURATION)
            start_y, final_y = HEIGHT//2, HEIGHT//4
            y_offset = start_y - (start_y - final_y) * progress
            spirit_surf = pygame.font.Font(None, 72).render("Spirit", True, WHITE)
            bound_surf = pygame.font.Font(None, 72).render("Bound", True, WHITE)
            bound_alpha = 255 if progress > 0.5 else int(255*(progress*2))
            spirit_surf.set_alpha(255); bound_surf.set_alpha(bound_alpha)
            total_width = spirit_surf.get_width() + 20 + bound_surf.get_width()
            x_start = WIDTH//2 - total_width//2
            screen.blit(spirit_surf, (x_start, y_offset))
            screen.blit(bound_surf, (x_start + spirit_surf.get_width() + 20, y_offset))
            if progress >= 1.0: title_anim_done = True

        if pygame.mixer.music.get_pos()/1000.0 >= HALF_TIME:
            menu_visible = True
            flash_alpha = 255

        pygame.display.flip()

    # ---------------- Main Menu Loop ----------------
    selected_index = 0
    time_val = 0
    running = True
    while running:
        dt = clock.tick(60)/1000.0
        time_val += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected_index = (selected_index - 1) % len(MENU_OPTIONS)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_index = (selected_index + 1) % len(MENU_OPTIONS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    choice = MENU_OPTIONS[selected_index]
                    if choice == "Quit":
                        running = False
                    elif choice == "Credits":
                        show_credits()
                    elif choice == "Settings":
                            play_video_overlay("HELP!.mp4", screen)
                    elif choice == "Play":
                        pygame.mixer.music.fadeout(1500)
                        pygame.time.delay(1500)
                        pygame.mixer.music.load(MUSIC_PATH)
                        pygame.mixer.music.play(-1, start=GAME_LOOP_START, fade_ms=2000)
                        pygame.mixer.music.set_volume(0.8)
                        spiritbound_game.Game().run()
                        pygame.mixer.music.fadeout(1500)
                        pygame.time.delay(1500)
                        pygame.mixer.music.load(MUSIC_PATH)
                        pygame.mixer.music.play(-1, start=MENU_LOOP_START, fade_ms=2000)
                        pygame.mixer.music.set_volume(0.5)

        # Draw
        screen.fill(DARK_BG)
        update_particles(dt, time_val)
        for p in particles:
            color = get_dynamic_color(time_val, p['angle'])
            pygame.draw.circle(screen, color, (int(p['x']), int(p['y'])), int(p['radius']))
        if menu_visible:
            draw_title(screen)
            draw_character(screen, WIDTH//2, HEIGHT//2 - 50, time_val)
            draw_menu(screen, selected_index, time_val)

        # Flash effect
        if menu_visible and flash_alpha > 0:
            flash_alpha = max(0, flash_alpha - 400*dt)
            flash_surface.set_alpha(flash_alpha)
            screen.blit(flash_surface, (0,0))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main_menu()

