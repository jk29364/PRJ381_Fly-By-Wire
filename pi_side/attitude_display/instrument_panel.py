import pygame
import math
import sys
import time

class FlightDataStream:
    def __init__(self):
        self.start_time = time.time()

    def get_telemetry(self):
        t = time.time() - self.start_time
        return {
            "pitch": math.sin(t * 0.8) * 18.0,
            "roll": math.sin(t * 0.5) * 25.0,
            "airspeed": 115.0 + math.sin(t * 0.4) * 35.0,
            "altitude": 2850.0 + math.sin(t * 0.3) * 600.0,
            "heading": (t * 4.0) % 360.0,
            "turn_rate": math.sin(t * 0.5) * 2.5,
            "vsi": math.cos(t * 0.3) * 1200.0,
            "ball": math.sin(t * 0.9) * 0.4
        }

WINDOW_W, WINDOW_H = 1050, 720
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
ORANGE = (240, 120, 20)
GREEN = (40, 180, 70)
RED = (220, 40, 40)

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

def draw_airspeed(surface, cx, cy, r, speed):
    pygame.draw.circle(surface, BLACK, (cx, cy), r)
    font_s = pygame.font.SysFont("arial", 11, bold=True)
    font_l = pygame.font.SysFont("arial", 13, bold=True)

    def k_to_rad(knots):
        deg = 30 + (knots - 40) * (300.0 / 200.0)
        return math.radians(deg - 90)

    pygame.draw.arc(surface, WHITE, (cx-r+12, cy-r+12, (r-12)*2, (r-12)*2), -k_to_rad(85), -k_to_rad(40), 6)
    pygame.draw.arc(surface, GREEN, (cx-r+18, cy-r+18, (r-18)*2, (r-18)*2), -k_to_rad(165), -k_to_rad(55), 6)
    pygame.draw.arc(surface, YELLOW, (cx-r+18, cy-r+18, (r-18)*2, (r-18)*2), -k_to_rad(200), -k_to_rad(165), 6)

    red_rad = k_to_rad(200)
    pygame.draw.line(surface, RED, (cx + (r-25)*math.cos(red_rad), cy + (r-25)*math.sin(red_rad)),
                     (cx + (r-10)*math.cos(red_rad), cy + (r-10)*math.sin(red_rad)), 4)

    for k in range(40, 245, 10):
        rad = k_to_rad(k)
        is_major = (k % 20 == 0)
        line_len = 14 if is_major else 8
        x1 = cx + (r - 10) * math.cos(rad)
        y1 = cy + (r - 10) * math.sin(rad)
        x2 = cx + (r - 10 - line_len) * math.cos(rad)
        y2 = cy + (r - 10 - line_len) * math.sin(rad)
        pygame.draw.line(surface, WHITE, (x1, y1), (x2, y2), 2 if is_major else 1)

        if is_major:
            tx = cx + (r - 34) * math.cos(rad)
            ty = cy + (r - 34) * math.sin(rad)
            txt = font_s.render(str(k), True, WHITE)
            surface.blit(txt, txt.get_rect(center=(tx, ty)))

    lbl1 = font_l.render("AIRSPEED", True, WHITE)
    lbl2 = font_s.render("KNOTS", True, WHITE)
    surface.blit(lbl1, lbl1.get_rect(center=(cx, cy - 35)))
    surface.blit(lbl2, lbl2.get_rect(center=(cx, cy + 35)))

    sp_clamped = max(40, min(240, speed))
    n_rad = k_to_rad(sp_clamped)
    nx = cx + (r - 18) * math.cos(n_rad)
    ny = cy + (r - 18) * math.sin(n_rad)
    pygame.draw.line(surface, WHITE, (cx, cy), (nx, ny), 3)
    pygame.draw.circle(surface, BEZEL_MID, (cx, cy), 10)
    pygame.draw.circle(surface, WHITE, (cx, cy), 4)

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

def draw_altimeter(surface, cx, cy, r, altitude):
    pygame.draw.circle(surface, BLACK, (cx, cy), r)
    font_num = pygame.font.SysFont("arial", 16, bold=True)
    font_s = pygame.font.SysFont("arial", 11, bold=True)

    for i in range(10):
        angle = i * 36.0 - 90.0
        rad = math.radians(angle)

        x1 = cx + (r - 10) * math.cos(rad)
        y1 = cy + (r - 10) * math.sin(rad)
        x2 = cx + (r - 24) * math.cos(rad)
        y2 = cy + (r - 24) * math.sin(rad)
        pygame.draw.line(surface, WHITE, (x1, y1), (x2, y2), 3)

        tx = cx + (r - 38) * math.cos(rad)
        ty = cy + (r - 38) * math.sin(rad)
        txt = font_num.render(str(i), True, WHITE)
        surface.blit(txt, txt.get_rect(center=(tx, ty)))

        for sub in range(1, 5):
            sub_rad = math.radians(angle + sub * 7.2)
            sx1 = cx + (r - 10) * math.cos(sub_rad)
            sy1 = cy + (r - 10) * math.sin(sub_rad)
            sx2 = cx + (r - 18) * math.cos(sub_rad)
            sy2 = cy + (r - 18) * math.sin(sub_rad)
            pygame.draw.line(surface, WHITE, (sx1, sy1), (sx2, sy2), 1)

    lbl = font_s.render("ALT", True, WHITE)
    surface.blit(lbl, lbl.get_rect(center=(cx + 35, cy - 15)))

    pygame.draw.rect(surface, BEZEL_DARK, (cx + 20, cy + 10, 42, 18))
    p_txt = font_s.render("29.92", True, WHITE)
    surface.blit(p_txt, p_txt.get_rect(center=(cx + 41, cy + 19)))

    rad_10k = math.radians((altitude / 100000.0) * 360.0 - 90.0)
    pygame.draw.line(surface, WHITE, (cx, cy), (cx + (r - 20) * math.cos(rad_10k), cy + (r - 20) * math.sin(rad_10k)), 1)

    rad_1k = math.radians((altitude % 10000.0 / 10000.0) * 360.0 - 90.0)
    k_x = cx + (r - 45) * math.cos(rad_1k)
    k_y = cy + (r - 45) * math.sin(rad_1k)
    pygame.draw.line(surface, WHITE, (cx, cy), (k_x, k_y), 5)

    rad_100 = math.radians((altitude % 1000.0 / 1000.0) * 360.0 - 90.0)
    h_x = cx + (r - 18) * math.cos(rad_100)
    h_y = cy + (r - 18) * math.sin(rad_100)
    pygame.draw.line(surface, WHITE, (cx, cy), (h_x, h_y), 3)

    pygame.draw.circle(surface, BEZEL_MID, (cx, cy), 8)
    pygame.draw.circle(surface, BEZEL_MID, (cx - r + 15, cy + r - 15), 14)

def draw_turn_coordinator(surface, cx, cy, r, turn_rate, ball_pos):
    pygame.draw.circle(surface, BLACK, (cx, cy), r)
    font_s = pygame.font.SysFont("arial", 11, bold=True)
    font_m = pygame.font.SysFont("arial", 12, bold=True)

    for sign, label in [(-1, "L"), (1, "R")]:
        pygame.draw.line(surface, WHITE, (cx + sign * (r - 40), cy), (cx + sign * (r - 12), cy), 3)
        rad = math.radians(90 + sign * 20)
        x1 = cx + (r - 35) * math.cos(rad)
        y1 = cy - (r - 35) * math.sin(rad)
        x2 = cx + (r - 12) * math.cos(rad)
        y2 = cy - (r - 12) * math.sin(rad)
        pygame.draw.line(surface, WHITE, (x1, y1), (x2, y2), 4)

        txt = font_m.render(label, True, WHITE)
        surface.blit(txt, txt.get_rect(center=(cx + sign * (r - 25), cy + 30)))

    lbl1 = font_s.render("D.C. ELEC.", True, WHITE)
    lbl2 = font_s.render("TURN COORDINATOR", True, WHITE)
    lbl3 = font_s.render("2 MIN.", True, WHITE)
    lbl4 = font_s.render("NO PITCH INFORMATION", True, WHITE)

    surface.blit(lbl1, lbl1.get_rect(center=(cx, cy - 55)))
    surface.blit(lbl2, lbl2.get_rect(center=(cx, cy + 18)))
    surface.blit(lbl3, lbl3.get_rect(center=(cx, cy + 34)))
    surface.blit(lbl4, lbl4.get_rect(center=(cx, cy + 72)))

    pygame.draw.arc(surface, WHITE, (cx - 50, cy + 38, 100, 30), math.radians(200), math.radians(340), 2)
    b_x = cx + ball_pos * 30
    pygame.draw.circle(surface, WHITE, (int(b_x), cy + 50), 7)

    ac_surf = pygame.Surface((100, 30), pygame.SRCALPHA)
    pygame.draw.circle(ac_surf, WHITE, (50, 15), 4)
    pygame.draw.line(ac_surf, WHITE, (10, 15), (90, 15), 4)
    pygame.draw.line(ac_surf, WHITE, (50, 5), (50, 25), 3)

    roll_angle = max(-30, min(30, turn_rate * 12.0))
    rot_ac = pygame.transform.rotate(ac_surf, -roll_angle)
    surface.blit(rot_ac, rot_ac.get_rect(center=(cx, cy - 15)))

def draw_heading_indicator(surface, cx, cy, r, heading):
    pygame.draw.circle(surface, BLACK, (cx, cy), r)
    font_s = pygame.font.SysFont("arial", 12, bold=True)

    card_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)

    headings = {0: "N", 3: "3", 6: "6", 9: "E", 12: "12", 15: "15",
                 18: "S", 21: "21", 24: "24", 27: "W", 30: "30", 33: "33"}

    for deg in range(0, 360, 5):
        rad = math.radians(deg - 90)
        is_major = (deg % 30 == 0)
        is_mid = (deg % 10 == 0)
        l_len = 16 if is_major else (10 if is_mid else 6)

        x1 = r + (r - 8) * math.cos(rad)
        y1 = r + (r - 8) * math.sin(rad)
        x2 = r + (r - 8 - l_len) * math.cos(rad)
        y2 = r + (r - 8 - l_len) * math.sin(rad)
        pygame.draw.line(card_surf, WHITE, (x1, y1), (x2, y2), 2 if is_major else 1)

        if is_major:
            val = deg // 10
            lbl_text = headings.get(val, str(val))
            txt = font_s.render(lbl_text, True, WHITE)
            tx = r + (r - 32) * math.cos(rad)
            ty = r + (r - 32) * math.sin(rad)
            card_surf.blit(txt, txt.get_rect(center=(tx, ty)))

    rot_card = pygame.transform.rotate(card_surf, heading)
    surface.blit(rot_card, rot_card.get_rect(center=(cx, cy)))

    ac_color = ORANGE
    pygame.draw.line(surface, ac_color, (cx - 40, cy), (cx + 40, cy), 3)
    pygame.draw.line(surface, ac_color, (cx, cy - 45), (cx, cy + 35), 3)
    pygame.draw.line(surface, ac_color, (cx - 18, cy + 28), (cx + 18, cy + 28), 3)

    pygame.draw.polygon(surface, ORANGE, [(cx, cy - r + 10), (cx - 7, cy - r + 22), (cx + 7, cy - r + 22)])

    pygame.draw.circle(surface, BEZEL_MID, (cx - r + 15, cy + r - 15), 14)

def draw_vsi(surface, cx, cy, r, vsi_rate):
    pygame.draw.circle(surface, BLACK, (cx, cy), r)
    font_s = pygame.font.SysFont("arial", 11, bold=True)
    font_m = pygame.font.SysFont("arial", 14, bold=True)

    ticks = [0, 5, 10, 15, 20]

    for t in ticks:
        deg_up = 180 - (t / 20.0) * 150.0
        rad_u = math.radians(deg_up)
        pygame.draw.line(surface, WHITE, (cx + (r-10)*math.cos(rad_u), cy + (r-10)*math.sin(rad_u)),
                         (cx + (r-24)*math.cos(rad_u), cy + (r-24)*math.sin(rad_u)), 2)
        if t in [5, 10, 15, 20]:
            txt = font_m.render(str(t // 5 if t >= 5 else t), True, WHITE)
            surface.blit(txt, txt.get_rect(center=(cx + (r-36)*math.cos(rad_u), cy + (r-36)*math.sin(rad_u))))

        deg_dn = 180 + (t / 20.0) * 150.0
        rad_d = math.radians(deg_dn)
        pygame.draw.line(surface, WHITE, (cx + (r-10)*math.cos(rad_d), cy + (r-10)*math.sin(rad_d)),
                         (cx + (r-24)*math.cos(rad_d), cy + (r-24)*math.sin(rad_d)), 2)
        if t in [5, 10, 15, 20]:
            txt = font_m.render(str(t // 5 if t >= 5 else t), True, WHITE)
            surface.blit(txt, txt.get_rect(center=(cx + (r-36)*math.cos(rad_d), cy + (r-36)*math.sin(rad_d))))

    lbl1 = font_s.render("VERTICAL SPEED", True, WHITE)
    lbl2 = font_s.render("THOUSANDS PER MIN", True, WHITE)
    lbl_up = font_s.render("UP", True, WHITE)
    lbl_dn = font_s.render("DN", True, WHITE)

    surface.blit(lbl1, lbl1.get_rect(center=(cx + 15, cy - 30)))
    surface.blit(lbl2, lbl2.get_rect(center=(cx + 15, cy - 16)))
    surface.blit(lbl_up, lbl_up.get_rect(center=(cx - 40, cy - 35)))
    surface.blit(lbl_dn, lbl_dn.get_rect(center=(cx - 40, cy + 35)))

    clamped_vsi = max(-2000.0, min(2000.0, vsi_rate))
    vsi_deg = 180.0 - (clamped_vsi / 2000.0) * 150.0
    vsi_rad = math.radians(vsi_deg)

    nx = cx + (r - 20) * math.cos(vsi_rad)
    ny = cy + (r - 20) * math.sin(vsi_rad)
    pygame.draw.line(surface, WHITE, (cx, cy), (nx, ny), 3)
    pygame.draw.circle(surface, BEZEL_MID, (cx, cy), 8)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Aviation Six-Pack Flight Instrument Panel")
    clock = pygame.time.Clock()

    data_stream = FlightDataStream()

    r = 115
    cols = [185, 525, 865]
    rows = [185, 525]

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

            for cy in rows:
                for cx in cols:
                    draw_gauge_bezel(screen, cx, cy, r)

            draw_airspeed(screen, cols[0], rows[0], r, data["airspeed"])
            draw_attitude(screen, cols[1], rows[0], r, data["pitch"], data["roll"])
            draw_altimeter(screen, cols[2], rows[0], r, data["altitude"])

            draw_turn_coordinator(screen, cols[0], rows[1], r, data["turn_rate"], data["ball"])
            draw_heading_indicator(screen, cols[1], rows[1], r, data["heading"])
            draw_vsi(screen, cols[2], rows[1], r, data["vsi"])

            pygame.display.flip()
            clock.tick(FPS)

    except KeyboardInterrupt:
        print("\nExiting Flight Instrument Panel...")
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
