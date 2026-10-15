import math
import time


def accel_pitch(ax, ay, az):
    """
    Works out pitch (nose up/down) from accelerometer data.
    """
    angle_radians = math.atan2(-ax, math.sqrt(ay**2 + az**2))
    angle_degrees = math.degrees(angle_radians)
    return angle_degrees


def accel_roll(ax, ay, az):
    """
    Works out roll (tilt left/right) from accelerometer data.
    """
    angle_radians = math.atan2(ay, az)
    angle_degrees = math.degrees(angle_radians)
    return angle_degrees


def gyro_pitch(previous_pitch, gy, dt):
    """
    Works out new pitch using only the gyroscope.
    Adds a tiny bit of rotation onto the old angle.
    """
    change = gy * dt
    new_pitch = previous_pitch + change
    return new_pitch


def gyro_roll(previous_roll, gx, dt):
    """
    Works out new roll using only the gyroscope.
    """
    change = gx * dt
    new_roll = previous_roll + change
    return new_roll


def complementary_filter(previous_angle, gyro_rate, accel_angle, dt, alpha=0.98):
    """
    Combines gyroscope and accelerometer readings into one
    stable angle. Trusts the gyro most of the time (smooth),
    but nudges toward the accelerometer to stop drift building up.
    """
    gyro_estimate = previous_angle + (gyro_rate * dt)
    new_angle = alpha * gyro_estimate + (1 - alpha) * accel_angle
    return new_angle


class AttitudeFilter:
    """
    Turns raw MPU6050 sensor data into stable pitch and roll angles,
    using a complementary filter (blends accelerometer + gyroscope).
    """

    def __init__(self, alpha=0.98):
        self.pitch = 0.0
        self.roll = 0.0
        self.alpha = alpha
        self.last_time = None          # set by the first update()

    def _accel_pitch(self, ax, ay, az):
        return math.degrees(math.atan2(-ax, math.sqrt(ay**2 + az**2)))

    def _accel_roll(self, ax, ay, az):
        return math.degrees(math.atan2(ay, az))

    def update(self, ax, ay, az, gx, gy, gz, timestamp=None):
        """
        Call this once per NEW sensor sample (not once per display frame, or the gyro
        gets integrated several times over).
        timestamp: when the sample arrived (time.monotonic()); defaults to now.
        Returns (pitch, roll) in degrees.
        """
        current_time = timestamp if timestamp is not None else time.monotonic()

        accel_pitch = self._accel_pitch(ax, ay, az)
        accel_roll = self._accel_roll(ax, ay, az)

        if self.last_time is None:
            # First sample: start from what the accelerometer says instead of from 0,
            # and don't integrate the gyro over the time since the program started.
            self.pitch = accel_pitch
            self.roll = accel_roll
            self.last_time = current_time
            return self.pitch, self.roll

        dt = max(0.0, min(current_time - self.last_time, 0.5))
        self.last_time = current_time

        gyro_pitch = self.pitch + (gy * dt)
        gyro_roll = self.roll + (gx * dt)

        self.pitch = self.alpha * gyro_pitch + (1 - self.alpha) * accel_pitch
        self.roll = self.alpha * gyro_roll + (1 - self.alpha) * accel_roll

        return self.pitch, self.roll
