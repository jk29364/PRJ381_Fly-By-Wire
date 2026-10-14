import pygame
import math
import sys
import time

# Sample data, only used when instrument_panel.py is run on its own.
# When instrument_main.py runs, it replaces pitch and roll with the filtered
# values and adds the raw sensor numbers under "raw".
class FlightDataStream:
    def __init__(self):
        self.start_time = time.time()

    def get_telemetry(self):
        t = time.time() - self.start_time
        return {
            "pitch": math.sin(t * 0.8) * 18.0,
            "roll": math.sin(t * 0.5) * 25.0,
            "raw": None
        }

WINDOW_W, WINDOW_H = 1000, 620
FPS = 60

PANEL_GREY = (112, 116, 122)
PANEL_DARK = (40, 42, 45)
BEZEL_DARK = (22, 23, 25)
BEZEL_MID = (55, 58, 62)
BEZEL_LIGHT = (130, 135, 142)

SKY_CYAN = (42, 158, 238)
EARTH_BROWN = (108, 62, 28)
WHITE = (255, 255, 255)
BLACK = (10, 10, 12)
YELLOW = (245, 210, 15)


def draw_screw(surface, x, y, size=11):
    pygame.draw.circle(surface, BLACK, (x, y), size)
    pygame.draw.circle(surface, BEZEL_MID, (x, y), size - 2)
    pygame.draw.circle(surface, BEZEL_LIGHT, (x - 2, y - 2), size - 5)
    pygame.draw.line(surface, BLACK, (x - 4, y - 4), (x + 4, y + 4), 2)
    pygame.draw.line(surface, BLACK, (x - 4, y + 4), (x + 4, y - 4), 2)

def draw_gauge_bezel(surface, cx, cy, radius):
    for angle in [45, 135, 225, 315]:
        rad = math.radians(angle)
        sx = int(cx + (radius + 22) * math.cos(rad))
        sy = int(cy + (radius + 22) * math.sin(rad))
        draw_screw(surface, sx, sy, 8)

    pygame.draw.circle(surface, BLACK, (cx, cy), radius + 15)
    pygame.draw.circle(surface, BEZEL_DARK, (cx, cy), radius + 12)
    pygame.draw.circle(surface, BEZEL_MID, (cx, cy), radius + 6, 2)
    pygame.draw.circle(surface, BEZEL_DARK, (cx, cy), radius + 3)

def draw_attitude(surface, cx, cy, r, pitch, roll):
    mask_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(mask_surf, (255, 255, 255), (r, r), r)

    h_size = r * 3
    horizon = pygame.Surface((h_size, h_size), pygame.SRCALPHA)
    horizon.fill(SKY_CYAN)

    pitch_shift = pitch * 3.5
    pygame.draw.rect(horizon, EARTH_BROWN, (0, h_size // 2 + pitch_shift, h_size, h_size))
    pygame.draw.line(horizon, WHITE, (0, h_size // 2 + pitch_shift), (h_size, h_size // 2 + pitch_shift), 3)

    font_p = pygame.font.SysFont("arial", 11, bold=True)
    for p in range(-80, 85, 5):
        if p == 0: continue
        ly = h_size // 2 + pitch_shift - (p * 3.5)
        if 0 < ly < h_size:
            major = (p % 10 == 0)
            lw = 44 if major else 22
            pygame.draw.line(horizon, WHITE, (h_size//2 - lw//2, ly), (h_size//2 + lw//2, ly), 2)
            if major:
                t = font_p.render(str(abs(p)), True, WHITE)
                horizon.blit(t, (h_size//2 - lw//2 - 18, ly - 6))
                horizon.blit(t, (h_size//2 + lw//2 + 5, ly - 6))

    center_y = h_size // 2 + pitch_shift
    for offset in [-90, -45, 0, 45, 90]:
        pygame.draw.line(horizon, WHITE, (h_size//2, center_y), (h_size//2 + offset * 2, center_y + 200), 2)

    rot_horizon = pygame.transform.rotate(horizon, -roll)
    rot_rect = rot_horizon.get_rect(center=(r, r))

    gauge_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    gauge_surf.blit(rot_horizon, rot_rect.topleft)
    gauge_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(gauge_surf, (cx - r, cy - r))

    for bank in [-60, -30, -20, -10, 0, 10, 20, 30, 60]:
        rad = math.radians(bank - 90)
        x1 = cx + (r - 2) * math.cos(rad)
        y1 = cy + (r - 2) * math.sin(rad)
        x2 = cx + (r - (22 if bank % 30 == 0 else 12)) * math.cos(rad)
        y2 = cy + (r - (22 if bank % 30 == 0 else 12)) * math.sin(rad)
        pygame.draw.line(surface, WHITE, (x1, y1), (x2, y2), 2)

    tri_y = cy - r + 16
    pygame.draw.polygon(surface, YELLOW, [(cx, tri_y), (cx - 10, tri_y - 16), (cx + 10, tri_y - 16)])

    pygame.draw.rect(surface, YELLOW, (cx - 75, cy - 4, 50, 8))
    pygame.draw.rect(surface, BLACK, (cx - 75, cy - 4, 50, 8), 2)
    pygame.draw.rect(surface, YELLOW, (cx + 25, cy - 4, 50, 8))
    pygame.draw.rect(surface, BLACK, (cx + 25, cy - 4, 50, 8), 2)
    pygame.draw.circle(surface, YELLOW, (cx, cy), 6)
    pygame.draw.circle(surface, BLACK, (cx, cy), 6, 2)
    pygame.draw.arc(surface, YELLOW, (cx - 20, cy - 8, 40, 40), math.radians(200), math.radians(340), 6)

    pygame.draw.circle(surface, BEZEL_DARK, (cx, cy + r - 8), 16)
    pygame.draw.circle(surface, BEZEL_MID, (cx, cy + r - 8), 12)

def draw_readout(surface, x, y, w, h, data):
    """Text panel next to the gauge: filtered pitch/roll, then the raw sensor numbers."""
    title_font = pygame.font.SysFont("arial", 18, bold=True)
    value_font = pygame.font.SysFont("consolas,couriernew,dejavusansmono", 20, bold=True)
    small_font = pygame.font.SysFont("arial", 14, bold=True)

    pygame.draw.rect(surface, BLACK, (x, y, w, h), border_radius=10)
    pygame.draw.rect(surface, BEZEL_MID, (x, y, w, h), 3, border_radius=10)

    line_y = y + 22

    def heading(text):
        nonlocal line_y
        surface.blit(title_font.render(text, True, YELLOW), (x + 22, line_y))
        line_y += 36

    def row(label, value, unit):
        nonlocal line_y
        text = "       --" if value is None else f"{value:+9.3f}"
        surface.blit(value_font.render(label, True, WHITE), (x + 22, line_y))
        surface.blit(value_font.render(text, True, WHITE), (x + 100, line_y))
        surface.blit(small_font.render(unit, True, BEZEL_LIGHT), (x + 250, line_y + 4))
        line_y += 32

    heading("ATTITUDE (filtered)")
    row("PITCH", data["pitch"], "deg")
    row("ROLL", data["roll"], "deg")

    line_y += 18
    heading("RAW SENSOR DATA")
    raw = data.get("raw")
    if raw is None:
        surface.blit(small_font.render("no raw data yet", True, BEZEL_LIGHT), (x + 22, line_y))
        return

    row("AX", raw.get("ax"), "g")
    row("AY", raw.get("ay"), "g")
    row("AZ", raw.get("az"), "g")
    row("GX", raw.get("gx"), "deg/s")
    row("GY", raw.get("gy"), "deg/s")
    row("GZ", raw.get("gz"), "deg/s")

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Attitude Indicator")
    clock = pygame.time.Clock()

    data_stream = FlightDataStream()

    r = 230                        # gauge radius
    gauge_x, gauge_y = 310, 310    # gauge centre

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    raise KeyboardInterrupt

            data = data_stream.get_telemetry()

            screen.fill(PANEL_GREY)

            for x in range(30, WINDOW_W, 120):
                draw_screw(screen, x, 20)
                draw_screw(screen, x, WINDOW_H - 20)
            for y in range(80, WINDOW_H - 80, 110):
                draw_screw(screen, 20, y)
                draw_screw(screen, WINDOW_W - 20, y)

            draw_gauge_bezel(screen, gauge_x, gauge_y, r)
            draw_attitude(screen, gauge_x, gauge_y, r, data["pitch"], data["roll"])
            draw_readout(screen, 620, 65, 330, 490, data)

            pygame.display.flip()
            clock.tick(FPS)

    except KeyboardInterrupt:
        print("\nExiting Attitude Indicator...")
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
