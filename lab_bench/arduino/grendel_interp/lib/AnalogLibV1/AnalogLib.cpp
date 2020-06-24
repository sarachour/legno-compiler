#include "AnalogLib.h"

void print_log (const char * message) {
  // trap for printing error
  if(LEVEL >= LOG_LEVEL){
    Serial.print("AC:>[msg] ");
    Serial.println(message);
    Serial.flush();
  }
}
void print_info (const char * message) {
  // trap for printing error
  if(LEVEL >= INFO_LEVEL){
    Serial.print("AC:>[msg] ");
    Serial.println(message);
    Serial.flush();
  }
}
void print_debug (const char * message) {
  // trap for printing error
  if(LEVEL >= DEBUG_LEVEL){
    Serial.print("AC:>[msg] ");
    Serial.println(message);
    Serial.flush();
  }
}

void print_level(const char * message, int level){
  switch(level){
  case LOG_LEVEL: print_log(message); break;
  case DEBUG_LEVEL: print_debug(message); break;
  case INFO_LEVEL: print_info(message); break;
  }
}
static void error (
                   const char * message
                   ) {
  // trap for printing error
  Serial.print("AC:>[msg] ERROR: ");
  Serial.println(message);
  Serial.flush();
  //close serial connection.
  Serial.end();
  while(true){
    delay(1000);
  }
}
