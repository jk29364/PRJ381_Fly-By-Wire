# Attitude Display

This folder contains the software attitude indicator for the 
Fly-By-Wire project. It takes raw sensor data, calculates the 
aircraft's pitch and roll, and displays it as a live instrument panel.

## Files

- attitude_filter.py — Converts raw MPU6050 accelerometer and 
  gyroscope data into stable pitch/roll angles using a complementary 
  filter. Written by Alexander Solomon.
- arduino_receiver.py — Provides mock sensor data (ax, ay, az, gx, 
  gy, gz) for testing without real hardware connected. Written by 
  Reabetswe Matake.
- instrument_panel.py — Draws the six-instrument dashboard (airspeed, 
  attitude, altimeter, turn coordinator, heading indicator, VSI) using 
  pygame. Written by Reabetswe Matake.
- main.py — Connects the three files above: pulls mock sensor data, 
  runs it through the filter, and feeds the result into the display.

## Requirements

- Python 3.x
- pygame

Install pygame with this command:

pip install pygame

## How to run

1. Open a terminal inside this folder (pi_side/attitude_display)
2. Install pygame (see above) if not already installed
3. Run this command:

python main.py

A window should open showing the instrument panel. The attitude 
indicator (top-middle gauge) will tilt based on data from the mock 
sensor receiver.

## Notes

- Currently uses mock sensor data (arduino_receiver.py) instead of 
  a real MPU6050 connection, for development and testing purposes.
- The pitch sign may need calibration once real hardware is connected, 
  as the accelerometer's positive/negative direction depends on 
  physical sensor orientation.
