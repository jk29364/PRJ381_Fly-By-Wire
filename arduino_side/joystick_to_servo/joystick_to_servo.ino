#include <Servo.h>

const int SERVO_COUNT = 6; 
Servo servos[SERVO_COUNT];
const int servoPins[SERVO_COUNT] = {2, 3, 4, 5, 6, 7}; 

void setup() {
  Serial.begin(115200);
  
  for (int i = 0; i < SERVO_COUNT; i++) {
    servos[i].attach(servoPins[i]);
    servos[i].write(90); 
  }
}

void loop() {
  // Check if there is data in the buffer
  if (Serial.available() > 0) {
    
    // Peek at the first byte in line without removing it yet
    if (Serial.peek() == 255) {
      
      // Wait until the dummy byte + all servo bytes are fully ready
      if (Serial.available() >= (SERVO_COUNT + 1)) {
        
        Serial.read(); // Read and DISCARD the 255 dummy byte (soaking up the latency)
        
        byte angles[SERVO_COUNT];
        // Instantly read the actual clean servo angles that follow
        Serial.readBytes((char*)angles, SERVO_COUNT);
        
        for (int i = 0; i < SERVO_COUNT; i++) {
          int cleanAngle = constraint(angles[i], 0, 180);
          servos[i].write(cleanAngle);
        }
      }
    } else {
      // If the buffer gets misaligned and doesn't start with 255, 
      // dump the bad byte to find the next clean packet header
      Serial.read(); 
    }
  }
}

int constraint(int val, int minVal, int maxVal) {
  if (val < minVal) return minVal;
  if (val > maxVal) return maxVal;
  return val;
}
