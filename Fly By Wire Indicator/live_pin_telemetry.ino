/*
  Streams MPU6050 attitude inputs and the mapped control-surface PWM signals
  to arduino_receiver.py over the Uno hardware serial connection (USB and
  the HC-05 on D0/D1).

  Digital inputs: D2 kill switch (active low), D3/D5 ailerons,
  D6/D9 elevators, D10 rudder. MPU6050: SDA=A4, SCL=A5.
  Each PWM input must share a ground with the Uno. The 9600 baud rate
  matches the usual HC-05 data-mode default.
*/

#include <Wire.h>

const uint8_t MPU6050_ADDRESS = 0x68;
const uint8_t PIN_KILL_SWITCH = 2;
const uint8_t PIN_LEFT_AILERON = 3;
const uint8_t PIN_RIGHT_AILERON = 5;
const uint8_t PIN_LEFT_ELEVATOR = 6;
const uint8_t PIN_RIGHT_ELEVATOR = 9;
const uint8_t PIN_RUDDER = 10;
const unsigned long PWM_TIMEOUT_US = 25000;

bool writeMpuRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU6050_ADDRESS);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readMpuData(float &ax, float &ay, float &az,
                 float &gx, float &gy, float &gz) {
  Wire.beginTransmission(MPU6050_ADDRESS);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  const uint8_t requested = 14;
  if (Wire.requestFrom(MPU6050_ADDRESS, requested, true) != requested) {
    return false;
  }

  int16_t rawAx = (Wire.read() << 8) | Wire.read();
  int16_t rawAy = (Wire.read() << 8) | Wire.read();
  int16_t rawAz = (Wire.read() << 8) | Wire.read();
  Wire.read(); Wire.read(); // Temperature is not used by the dashboard.
  int16_t rawGx = (Wire.read() << 8) | Wire.read();
  int16_t rawGy = (Wire.read() << 8) | Wire.read();
  int16_t rawGz = (Wire.read() << 8) | Wire.read();

  ax = rawAx / 16384.0f;
  ay = rawAy / 16384.0f;
  az = rawAz / 16384.0f;
  gx = rawGx / 131.0f;
  gy = rawGy / 131.0f;
  gz = rawGz / 131.0f;
  return true;
}

unsigned long readPwmInput(uint8_t pin) {
  return pulseIn(pin, HIGH, PWM_TIMEOUT_US);
}

void setup() {
  pinMode(PIN_KILL_SWITCH, INPUT_PULLUP);
  pinMode(PIN_LEFT_AILERON, INPUT);
  pinMode(PIN_RIGHT_AILERON, INPUT);
  pinMode(PIN_LEFT_ELEVATOR, INPUT);
  pinMode(PIN_RIGHT_ELEVATOR, INPUT);
  pinMode(PIN_RUDDER, INPUT);

  Serial.begin(9600);
  Wire.begin();

  if (!writeMpuRegister(0x6B, 0x00) ||
      !writeMpuRegister(0x1B, 0x00) ||
      !writeMpuRegister(0x1C, 0x00)) {
    Serial.println(F("ERR:MPU6050_INIT"));
  }
}

void loop() {
  float ax, ay, az, gx, gy, gz;
  if (!readMpuData(ax, ay, az, gx, gy, gz)) {
    Serial.println(F("ERR:MPU6050_READ"));
    delay(100);
    return;
  }

  const unsigned long leftAileron = readPwmInput(PIN_LEFT_AILERON);
  const unsigned long rightAileron = readPwmInput(PIN_RIGHT_AILERON);
  const unsigned long leftElevator = readPwmInput(PIN_LEFT_ELEVATOR);
  const unsigned long rightElevator = readPwmInput(PIN_RIGHT_ELEVATOR);
  const unsigned long rudder = readPwmInput(PIN_RUDDER);
  const uint8_t killSwitch = digitalRead(PIN_KILL_SWITCH) == LOW ? 1 : 0;

  Serial.print(F("AX:")); Serial.print(ax, 4);
  Serial.print(F(" AY:")); Serial.print(ay, 4);
  Serial.print(F(" AZ:")); Serial.print(az, 4);
  Serial.print(F(" GX:")); Serial.print(gx, 2);
  Serial.print(F(" GY:")); Serial.print(gy, 2);
  Serial.print(F(" GZ:")); Serial.print(gz, 2);
  Serial.print(F(" LEFT_AILERON_US:")); Serial.print(leftAileron);
  Serial.print(F(" RIGHT_AILERON_US:")); Serial.print(rightAileron);
  Serial.print(F(" LEFT_ELEVATOR_US:")); Serial.print(leftElevator);
  Serial.print(F(" RIGHT_ELEVATOR_US:")); Serial.print(rightElevator);
  Serial.print(F(" RUDDER_US:")); Serial.print(rudder);
  Serial.print(F(" KILL:")); Serial.println(killSwitch);

  delay(20);
}
