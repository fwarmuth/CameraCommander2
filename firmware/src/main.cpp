#include <Arduino.h>
#include "protocol.h"

void setup() {
  Serial.begin(9600);
  delay(100);
  Serial.print("Dual-axis turntable – firmware ");
  Serial.println(FW_VERSION);
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    cmd = toupper(cmd);
    
    switch(cmd) {
      case CMD_VERSION:
        Serial.print(REPLY_VERSION);
        Serial.println(FW_VERSION);
        break;
      case CMD_STATUS:
        Serial.println("STATUS 0.000 0.000 0");
        break;
      case CMD_ENABLE:
        Serial.println("OK DRIVERS ON");
        break;
      case CMD_DISABLE:
        Serial.println("OK DRIVERS OFF");
        break;
      case CMD_STOP:
        Serial.println("OK STOP");
        break;
      default:
        // Ignore unknowns or whitespace
        break;
    }
  }
}
