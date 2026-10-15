#include <Servo.h>
#include <Wire.h>

const int SERVO_COUNT = 6; 
Servo servos[SERVO_COUNT];
const int servoPins[SERVO_COUNT] = {2, 3, 4, 5, 6, 7}; 

const int MPU_ADDR = 0x68; 

void setup() {
  Serial.begin(9600); // Maintained at your locked 9600 baud configuration
  
  // Center all control surface linkages on initialization
  for (int i = 0; i < SERVO_COUNT; i++) {
    servos[i].attach(servoPins[i]);
    servos[i].write(90); 
  }

  // Wake up MPU6050
  Wire.begin();
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); 
  Wire.write(0);    
  Wire.endTransmission(true);
}


const byte HEADER_1 = 0x5A; // Safe unique identifier character 'Z'
const byte HEADER_2 = 0xA5; // Safe unique identifier character 'ñ'

void loop() {
  // Wait until we have enough bytes for headers + payload (2 headers + 6 servo bytes = 8 bytes)
  if (Serial.available() >= (SERVO_COUNT + 2)) {
    
    // Check if the front of the buffer matches our strict 2-byte magic alignment sequence
    if (Serial.peek() == HEADER_1) {
      Serial.read(); // Consume Header 1
      
      if (Serial.peek() == HEADER_2) {
        Serial.read(); // Consume Header 2
        
        // Read clean target angles safely
        byte angles[SERVO_COUNT];
        Serial.readBytes((char*)angles, SERVO_COUNT);
        
        // Drive physical motor outputs safely
        for (int i = 0; i < SERVO_COUNT; i++) {
          int cleanAngle = constraint(angles[i], 45, 135); 
          servos[i].write(cleanAngle);
        }
        
        // ONLY send telemetry back after successfully receiving a valid control frame!
        transmitTelemetry();
      }
    } else {
      // Not our header, discard a single byte to clear out stray serial noise
      Serial.read();
    }
  }
}

void transmitTelemetry() {
  int16_t raw_ax, raw_ay, raw_az;
  int16_t raw_gx, raw_gy, raw_gz;
  int16_t raw_temp; 

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  if (Wire.available() >= 14) {
    raw_ax = (Wire.read() << 8) | Wire.read();
    raw_ay = (Wire.read() << 8) | Wire.read();
    raw_az = (Wire.read() << 8) | Wire.read();
    raw_temp = (Wire.read() << 8) | Wire.read();
    raw_gx = (Wire.read() << 8) | Wire.read();
    raw_gy = (Wire.read() << 8) | Wire.read();
    raw_gz = (Wire.read() << 8) | Wire.read();

    float ax = (float)raw_ax / 16384.0;
    float ay = (float)raw_ay / 16384.0;
    float az = (float)raw_az / 16384.0;
    float gx = (float)raw_gx / 131.0;
    float gy = (float)raw_gy / 131.0;
    float gz = (float)raw_gz / 131.0;

    Serial.print("TELEMETRY:");
    Serial.print(ax, 4);  Serial.print(",");
    Serial.print(ay, 4);  Serial.print(",");
    Serial.print(az, 4);  Serial.print(",");
    Serial.print(gx, 4);  Serial.print(",");
    Serial.print(gy, 4);  Serial.print(",");
    Serial.println(gz, 4); 
  }
}

int constraint(int val, int minVal, int maxVal) {
  if (val < minVal) return minVal;
  if (val > maxVal) return maxVal;
  return val;
}
