import math
import os
import sys

import pygame

from arduino_receiver import get_latest_data, start_receiver, stop_receiver

WINDOW_W, WINDOW_H = 1050, 720
FPS = 60

PANEL_GREY = (112, 116, 122)
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
    for angle in (45, 135, 225, 315):
        rad = math.radians(angle)
        screw_x = int(cx + (radius + 22) * math.cos(rad))
        screw_y = int(cy + (radius + 22) * math.sin(rad))
        draw_screw(surface, screw_x, screw_y, 8)

    pygame.draw.circle(surface, BLACK, (cx, cy), radius + 15)
    pygame.draw.circle(surface, BEZEL_DARK, (cx, cy), radius + 12)
    pygame.draw.circle(surface, BEZEL_MID, (cx, cy), radius + 6, 2)
    pygame.draw.circle(surface, BEZEL_DARK, (cx, cy), radius + 3)


def draw_attitude(surface, cx, cy, radius, pitch, roll, yaw):
    mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(mask, WHITE, (radius, radius), radius)

    horizon_size = radius * 3
    horizon = pygame.Surface((horizon_size, horizon_size), pygame.SRCALPHA)
    horizon.fill(SKY_CYAN)

    horizon_y = horizon_size // 2 + pitch * 3.5
    pygame.draw.rect(
        horizon, EARTH_BROWN,
        (0, horizon_y, horizon_size, horizon_size),
    )
    pygame.draw.line(
        horizon, WHITE, (0, horizon_y), (horizon_size, horizon_y), 3,
    )

    pitch_font = pygame.font.SysFont("arial", 11, bold=True)
    for pitch_mark in range(-80, 85, 5):
        if pitch_mark == 0:
            continue
        mark_y = horizon_y - pitch_mark * 3.5
        if 0 < mark_y < horizon_size:
            major = pitch_mark % 10 == 0
            mark_width = 44 if major else 22
            pygame.draw.line(
                horizon, WHITE,
                (horizon_size // 2 - mark_width // 2, mark_y),
                (horizon_size // 2 + mark_width // 2, mark_y),
                2,
            )
            if major:
                label = pitch_font.render(str(abs(pitch_mark)), True, WHITE)
                horizon.blit(
                    label,
                    (horizon_size // 2 - mark_width // 2 - 18, mark_y - 6),
                )
                horizon.blit(
                    label,
                    (horizon_size // 2 + mark_width // 2 + 5, mark_y - 6),
                )

    for offset in (-90, -45, 0, 45, 90):
        pygame.draw.line(
            horizon, WHITE,
            (horizon_size // 2, horizon_y),
            (horizon_size // 2 + offset * 2, horizon_y + 200),
            2,
        )

    rotated_horizon = pygame.transform.rotate(horizon, -roll)
    horizon_rect = rotated_horizon.get_rect(center=(radius, radius))
    gauge = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    gauge.blit(rotated_horizon, horizon_rect.topleft)
    gauge.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(gauge, (cx - radius, cy - radius))

    for bank in (-60, -30, -20, -10, 0, 10, 20, 30, 60):
        angle = math.radians(bank - 90)
        outer = (
            cx + (radius - 2) * math.cos(angle),
            cy + (radius - 2) * math.sin(angle),
        )
        tick_length = 22 if bank % 30 == 0 else 12
        inner = (
            cx + (radius - tick_length) * math.cos(angle),
            cy + (radius - tick_length) * math.sin(angle),
        )
        pygame.draw.line(surface, WHITE, outer, inner, 2)

    marker_y = cy - radius + 16
    pygame.draw.polygon(
        surface, YELLOW,
        ((cx, marker_y), (cx - 10, marker_y - 16), (cx + 10, marker_y - 16)),
    )
    pygame.draw.rect(surface, YELLOW, (cx - 75, cy - 4, 50, 8))
    pygame.draw.rect(surface, BLACK, (cx - 75, cy - 4, 50, 8), 2)
    pygame.draw.rect(surface, YELLOW, (cx + 25, cy - 4, 50, 8))
    pygame.draw.rect(surface, BLACK, (cx + 25, cy - 4, 50, 8), 2)
    pygame.draw.circle(surface, YELLOW, (cx, cy), 6)
    pygame.draw.circle(surface, BLACK, (cx, cy), 6, 2)
    pygame.draw.arc(
        surface, YELLOW, (cx - 20, cy - 8, 40, 40),
        math.radians(200), math.radians(340), 6,
    )

    pygame.draw.circle(surface, BEZEL_DARK, (cx, cy + radius - 8), 16)
    pygame.draw.circle(surface, BEZEL_MID, (cx, cy + radius - 8), 12)
    readout_font = pygame.font.SysFont("arial", 16, bold=True)
    readout = readout_font.render(
        f"PITCH {pitch:+.1f}°   ROLL {roll:+.1f}°   YAW {yaw:+.1f}°",
        True,
        WHITE,
    )
    surface.blit(readout, readout.get_rect(center=(cx, cy + radius + 38)))


def draw_waiting_message(surface, cx, cy):
    font = pygame.font.SysFont("arial", 16, bold=True)
    message = font.render("WAITING FOR SENSOR DATA", True, YELLOW)
    surface.blit(message, message.get_rect(center=(cx, cy)))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Live Pitch, Roll, and Yaw Attitude Indicator")
    clock = pygame.time.Clock()
    radius = 235
    center_x = WINDOW_W // 2
    center_y = WINDOW_H // 2 - 25
    yaw = 0.0
    last_yaw_sample = 0.0

    telemetry_port = os.environ.get("FBW_TELEMETRY_PORT")
    telemetry_baud = int(os.environ.get("FBW_TELEMETRY_BAUD", "9600"))
    start_receiver(port=telemetry_port, baudrate=telemetry_baud)
    try:
        while True:
            for event in pygame.event.get():
                if (event.type == pygame.QUIT
                        or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)):
                    raise KeyboardInterrupt

            data = get_latest_data()
            active = data["stream_active"] and data["attitude_available"]
            if active and data["last_update"] > last_yaw_sample:
                if last_yaw_sample:
                    elapsed = min(data["last_update"] - last_yaw_sample, 0.1)
                    yaw = (yaw + data["gz"] * elapsed + 180.0) % 360.0 - 180.0
                last_yaw_sample = data["last_update"]

            screen.fill(PANEL_GREY)
            for x in range(30, WINDOW_W, 120):
                draw_screw(screen, x, 20)
                draw_screw(screen, x, WINDOW_H - 20)
            for y in range(80, WINDOW_H - 80, 110):
                draw_screw(screen, 20, y)
                draw_screw(screen, WINDOW_W - 20, y)

            draw_gauge_bezel(screen, center_x, center_y, radius)
            if active:
                draw_attitude(
                    screen, center_x, center_y, radius,
                    data["pitch"], data["roll"], yaw,
                )
            else:
                draw_waiting_message(screen, center_x, center_y)

            pygame.display.flip()
            clock.tick(FPS)
    except KeyboardInterrupt:
        print("\nExiting attitude indicator...")
    finally:
        stop_receiver()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    main()
