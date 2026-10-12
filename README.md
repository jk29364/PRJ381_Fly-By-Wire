# PRJ381_Fly-By-Wire
The 3rd year project of Group 6 at Belgium Campus iTversity during the 2026 academic year.

## Live attitude indicator

The dashboard in `Fly By Wire Indicator` displays the connected artificial
horizon with MPU6050 pitch and roll plus relative yaw integrated from the
gyroscope. Upload `arduino_side/sensor_telemetry/sensor_telemetry.ino` to a
separate telemetry Uno and configure its HC-05 Bluetooth serial port before
starting the dashboard.

On Windows PowerShell:

```powershell
$env:FBW_TELEMETRY_PORT = "COM7"
$env:FBW_TELEMETRY_BAUD = "9600"
python "Fly By Wire Indicator\attitude_indicator 1.py"
```

