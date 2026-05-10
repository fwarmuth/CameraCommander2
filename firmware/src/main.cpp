#include <Arduino.h>
#include "protocol.h"
#include "GearedStepper.h"

// Hardware configuration
const int PAN_STEP_PIN = 12; // D6
const int PAN_DIR_PIN = 14;  // D5
const int TILT_STEP_PIN = 13; // D7
const int TILT_DIR_PIN = 15;  // D8
const int ENABLE_PIN = 4;     // D2

GearedStepper panStepper(PAN_STEP_PIN, PAN_DIR_PIN);
GearedStepper tiltStepper(TILT_STEP_PIN, TILT_DIR_PIN);

void setup() {
  Serial.begin(9600);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, HIGH); // Disabled by default

  panStepper.setMaxSpeed(1000);
  panStepper.setAcceleration(500);
  tiltStepper.setMaxSpeed(1000);
  tiltStepper.setAcceleration(500);

  delay(100);
  Serial.print("Dual-axis turntable – firmware ");
  Serial.println(FW_VERSION);
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    char cmd = toupper(line[0]);
    
    switch(cmd) {
      case CMD_VERSION:
        Serial.print(REPLY_VERSION);
        Serial.println(FW_VERSION);
        break;
      case CMD_STATUS:
        Serial.print(REPLY_STATUS);
        Serial.print(panStepper.currentAngle(), 3);
        Serial.print(" ");
        Serial.print(tiltStepper.currentAngle(), 3);
        Serial.print(" ");
        Serial.println(digitalRead(ENABLE_PIN) == LOW ? "1" : "0");
        break;
      case CMD_ENABLE:
        digitalWrite(ENABLE_PIN, LOW);
        panStepper.setCurrentAngle(0);
        tiltStepper.setCurrentAngle(0);
        Serial.println("OK DRIVERS ON");
        break;
      case CMD_DISABLE:
        digitalWrite(ENABLE_PIN, HIGH);
        Serial.println("OK DRIVERS OFF");
        break;
      case CMD_STOP:
        panStepper.stop();
        tiltStepper.stop();
        Serial.println("OK STOP");
        break;
      case CMD_MOVE: {
        float p, t;
        if (sscanf(line.c_str() + 1, "%f %f", &p, &t) == 2) {
          panStepper.moveToAngle(p);
          tiltStepper.moveToAngle(t);
          while (panStepper.distanceToGo() != 0 || tiltStepper.distanceToGo() != 0) {
            panStepper.run();
            tiltStepper.run();
            yield();
          }
          Serial.println(REPLY_DONE);
        } else {
          Serial.println("ERR Syntax");
        }
        break;
      }
      default:
        Serial.println("ERR Unknown");
        break;
    }
  }
  panStepper.run();
  tiltStepper.run();
  yield();
}
