"""Fly-by-wire ground station: run this file.

1. Shows the connection status screen while the Arduino link comes up.
2. Half a second after the connection succeeds, switches to the attitude display.
3. Every frame: reads the joystick, sends the 7 servo angles to the Arduino, and draws the
   attitude from the MPU6050 data that comes back.

Joystick: button 0 zeroes the attitude display (local only), button 2 / 4 switch the aileron
servos to 45 / back to 90 degrees. Button and axis numbers are in config.py.
"""
import pygame

import config
import connection_screen
import instrument_panel
from arduino_receiver import ArduinoLink, clamp_angle, STATE_CONNECTED
from attitude_filter import AttitudeFilter


def axis_to_angle(value):
    """Joystick axis (-1.0 .. 1.0) -> servo angle (45 .. 135, 90 at centre)."""
    value = max(-1.0, min(1.0, value))
    span = config.SERVO_MAX - config.SERVO_NEUTRAL
    return clamp_angle(config.SERVO_NEUTRAL + value * span)


def wrap_degrees(angle):
    return (angle + 180.0) % 360.0 - 180.0


class FlightController:
    """Plugs the joystick, the Arduino link and the attitude filter into the instrument panel."""

    def __init__(self, link):
        self.link = link
        self.filter = AttitudeFilter()
        self.joystick = None
        self.aileron_on = False
        self.servo_angles = [config.SERVO_NEUTRAL] * config.SERVO_COUNT

        self._last_seq = -1
        self._pitch = 0.0          # filtered, before zeroing
        self._roll = 0.0
        self._zero_pitch = 0.0
        self._zero_roll = 0.0

        self._ensure_joystick()    # open it now so button events are delivered from the start

    # ---------------------------------------------------------------- joystick
    def _ensure_joystick(self):
        """Pick up a joystick that was plugged in after start-up."""
        if self.joystick is None and pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            print(f"[SYSTEM] Flight controls linked: {self.joystick.get_name()}")

    def _axis(self, index):
        js = self.joystick
        if js is None or index >= js.get_numaxes():
            return 0.0
        try:
            value = js.get_axis(index)
        except pygame.error:                       # unplugged mid-flight
            self.joystick = None
            return 0.0
        return 0.0 if abs(value) < config.JOY_DEADZONE else value

    def handle_event(self, event):
        if event.type != pygame.JOYBUTTONDOWN:
            return
        if event.button == config.BUTTON_GYRO_ZERO:
            self._zero_pitch, self._zero_roll = self._pitch, self._roll
        elif event.button == config.BUTTON_AILERON_ON:
            self.aileron_on = True
        elif event.button == config.BUTTON_AILERON_OFF:
            self.aileron_on = False

    # ---------------------------------------------------------------- per-frame work
    def _update_servos(self):
        self._ensure_joystick()
        roll = self._axis(config.AXIS_ROLL)
        pitch = self._axis(config.AXIS_PITCH)
        yaw = self._axis(config.AXIS_YAW)

        if self.aileron_on:
            aileron_l, aileron_r = config.AILERON_L_ACTIVE_ANGLE, config.AILERON_R_ACTIVE_ANGLE
        else:
            aileron_l = aileron_r = config.AILERON_REST_ANGLE

        # Same order as config.SERVO_NAMES / the Arduino's servoPins[] = {4, 6, 7, 8, 9, 11, 12}
        self.servo_angles = [clamp_angle(a) for a in (
            axis_to_angle(yaw),        # D4  rudder
            axis_to_angle(pitch),     # D6  tail right (mirrored)
            axis_to_angle(-pitch),      # D7  tail left
            aileron_r,                 # D8  right wing inner (buttons)
            axis_to_angle(roll),      # D9  right wing outer (mirrored)
            aileron_l,                 # D11 left wing inner (buttons)
            axis_to_angle(-roll),       # D12 left wing outer
        )]
        self.link.set_servo_angles(self.servo_angles)

    def get_telemetry(self):
        self._update_servos()

        state, _ = self.link.get_status()
        raw = self.link.get_latest_data()
        if state == STATE_CONNECTED and raw["stream_active"]:
            if raw["seq"] != self._last_seq:       # filter once per NEW sample only
                self._last_seq = raw["seq"]
                self._pitch, self._roll = self.filter.update(
                    raw["ax"], raw["ay"], raw["az"], raw["gx"], raw["gy"], raw["gz"],
                    timestamp=raw["t"])
        else:
            raw = None

        return {
            "pitch": wrap_degrees(self._pitch - self._zero_pitch),
            "roll": wrap_degrees(self._roll - self._zero_roll),
            "raw": raw,
            "servos": self.servo_angles,
            "aileron_on": self.aileron_on,
            "link_ok": state == STATE_CONNECTED,
        }


def main():
    pygame.init()
    pygame.joystick.init()
    screen = pygame.display.set_mode((instrument_panel.WINDOW_W, instrument_panel.WINDOW_H))

    link = ArduinoLink()
    link.start()
    try:
        if connection_screen.run(screen, link):
            controller = FlightController(link)
            instrument_panel.run(screen, controller, on_event=controller.handle_event)
    except KeyboardInterrupt:
        pass
    finally:
        link.stop()
        pygame.quit()


if __name__ == "__main__":
    main()
