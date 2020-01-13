#include "Arduino.h"
/****************************************
Example Sound Level Sketch for the 
Adafruit Microphone Amplifier
****************************************/

int trigPin = 11;    // Trigger
int echoPin = 12;    // Echo
long duration;

void setup()
{
   Serial.begin(9600);
   analogWriteResolution(12);
   pinMode(trigPin, OUTPUT);
}

void loop()
{
  analogWrite(DAC0, 2037);
  delay(2500);
}
