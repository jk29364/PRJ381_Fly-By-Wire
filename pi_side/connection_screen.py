"""Connection status screen shown when main.py starts.

Stays up while the Arduino link is coming up, shows what is happening (or what went wrong),
and closes config.CONNECTED_SCREEN_HOLD seconds after the connection succeeds.
"""
import time

import pygame

import arduino_receiver as link_states
import config
import instrument_panel as ui   # reuse the same colours / window size

BG = (22, 23, 25)
PANEL = (40, 42, 45)
AMBER = (245, 170, 30)

_STATE_STYLE = {
    link_states.STATE_IDLE: ("STARTING", AMBER),
    link_states.STATE_OPENING: ("OPENING PORT", AMBER),
    link_states.STATE_WAITING: ("WAITING FOR ARDUINO", AMBER),
    link_states.STATE_CONNECTED: ("CONNECTED", ui.GREEN),
    link_states.STATE_LOST: ("WAITING FOR ARDUINO", AMBER),
    link_states.STATE_ERROR: ("CONNECTION FAILED", ui.RED),
}


def _draw(screen, state, message, spinner_phase):
    label, colour = _STATE_STYLE.get(state, ("...", AMBER))
    w, h = screen.get_size()
    cx = w // 2

    screen.fill(BG)
    card = pygame.Rect(0, 0, 620, 340)
    card.center = (cx, h // 2)
    pygame.draw.rect(screen, PANEL, card, border_radius=14)
    pygame.draw.rect(screen, ui.BEZEL_MID, card, 3, border_radius=14)

    title = ui._font("arial", 30).render("FLY-BY-WIRE", True, ui.YELLOW)
    screen.blit(title, title.get_rect(center=(cx, card.top + 48)))
    sub = ui._font("arial", 16).render("CONNECTION STATUS", True, ui.BEZEL_LIGHT)
    screen.blit(sub, sub.get_rect(center=(cx, card.top + 82)))

    info = ui._font("consolas,couriernew,dejavusansmono", 18)
    screen.blit(info.render(f"PORT  {config.SERIAL_PORT}", True, ui.WHITE), (card.left + 60, card.top + 120))
    screen.blit(info.render(f"BAUD  {config.BAUD_RATE}", True, ui.WHITE), (card.left + 60, card.top + 150))

    # status light + label
    light = (card.left + 78, card.top + 215)
    if state == link_states.STATE_CONNECTED:
        pygame.draw.circle(screen, colour, light, 13)
    elif state == link_states.STATE_ERROR:
        pygame.draw.circle(screen, colour, light, 13)
    else:                                         # pulsing while we wait
        pulse = 0.5 + 0.5 * abs(((spinner_phase * 1.5) % 2.0) - 1.0)
        pygame.draw.circle(screen, tuple(int(c * pulse) for c in colour), light, 13)
    pygame.draw.circle(screen, ui.BLACK, light, 13, 2)
    status = ui._font("arial", 26).render(label, True, colour)
    screen.blit(status, (light[0] + 28, light[1] - status.get_height() // 2))

    # detail line(s), wrapped to the card width
    detail_font = ui._font("arial", 15, False)
    y = card.top + 252
    words, line = message.split(), ""
    for word in words:
        trial = f"{line} {word}".strip()
        if detail_font.size(trial)[0] > card.width - 120 and line:
            screen.blit(detail_font.render(line, True, ui.BEZEL_LIGHT), (card.left + 60, y))
            y += 20
            line = word
        else:
            line = trial
        if y > card.bottom - 40:
            break
    if line:
        screen.blit(detail_font.render(line, True, ui.BEZEL_LIGHT), (card.left + 60, y))

    hint_text = ("Retrying every %g s. " % config.RECONNECT_INTERVAL
                 if state == link_states.STATE_ERROR else "") + "Press ESC to quit"
    hint = ui._font("arial", 13, False).render(hint_text, True, ui.BEZEL_MID)
    screen.blit(hint, hint.get_rect(center=(cx, h - 30)))


def run(screen, link):
    """Show the screen until the link is up (+ hold time). Returns True when connected,
    False if the user closed the window / pressed ESC first."""
    pygame.display.set_caption("Fly-By-Wire: connecting")
    clock = pygame.time.Clock()
    connected_at = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return False

        state, message = link.get_status()
        if state == link_states.STATE_CONNECTED and connected_at is None:
            connected_at = time.monotonic()

        _draw(screen, state, message, time.monotonic())
        pygame.display.flip()

        if connected_at is not None and time.monotonic() - connected_at >= config.CONNECTED_SCREEN_HOLD:
            return True
        clock.tick(30)
