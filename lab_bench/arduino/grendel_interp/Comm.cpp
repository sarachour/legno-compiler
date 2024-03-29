#include "Comm.h"
#include <Arduino.h>

namespace comm {
#define GRENDEL_BUFSIZ 512

byte INBUF[GRENDEL_BUFSIZ];
int WPOS=0;
int RPOS=0;
int MSGNO = 0;
int TRYNO = 0;
bool MSG_AVAILABLE =false;


bool read_mode(){
  return MSG_AVAILABLE;
}
void header(){
  Serial.print("\nAC:>");
}
void print_header(){
  header();
  Serial.print("[msg]");
}
void process_command(){
  header();
  Serial.println("[process]");
}
void done_command(){
  header();
  Serial.println("[done]");
  Serial.flush();
}

void payload(){
  header();
  Serial.print("[array]");
}
void data(const char * msg,const char * type_sig){
  header();
  Serial.print("[data][");
  Serial.print(type_sig);
  Serial.print("] ");
  Serial.println(msg);
  Serial.flush();
}
void response(const char * msg,int args){
  header();
  Serial.print("[resp][");
  Serial.print(args);
  Serial.print("]");
  Serial.println(msg);
  Serial.flush();
}
void error(const char * msg){
  while(1){
     header();
     Serial.print("[msg] ERROR : ");
     Serial.println(msg);
     Serial.flush();
     delay(100);
  }
}

void test(bool result, const char * msg){
  if(result){
    return;
  }
  else{
    error(msg);
  }
}
void reset(){
  MSG_AVAILABLE = false;
  WPOS = 0;
  RPOS = 0;
}
int write_pos(){
  return WPOS;
}

#define DELIMS 5
#define START_DELIM 254
#define END_DELIM 253

int _find_start(int delim_count){
  int n_delims = 0;

  for(int i=0; i < WPOS; i+= 1){
    if(n_delims == delim_count){
      return i;
    }
    if(INBUF[i] == START_DELIM){
      n_delims += 1;
    }
    else{
      n_delims = 0;
    }
  }
  error("no prefix found for message...");
}

int _find_end(){
  int n_delims = 0;
  for(int i=WPOS-1; i >= 0; i -= 1){
    if(INBUF[i] == END_DELIM){
      n_delims += 1;
    }
    else{
      return n_delims;
    }
  }
  return n_delims;
}


void listen(){
  if(MSG_AVAILABLE){
    print_header();
    Serial.println("<found endline>");
    return;
  }

  while(Serial.available() > 0){
    char recv = Serial.read();
    INBUF[WPOS] = recv;
    WPOS += 1;
    // last three characters are 253
    if(recv == END_DELIM && _find_end() == DELIMS){
      MSG_AVAILABLE = true;
      RPOS = _find_start(DELIMS);
      MSGNO += 1;
      return;
    }
  }
}

void* get_data_ptr(int offset){
   return &INBUF[offset];
}
void print_data(int offset){
   for(int idx=offset; idx < WPOS; idx += 1){
      print_header();
      Serial.print(idx);
      Serial.print(" ");
      Serial.println(INBUF[idx],HEX);
   }
}
int get_input(uint8_t* buf, int n_bytes){
  if(not MSG_AVAILABLE){
    return -1;
  }
  int siz = WPOS - RPOS < n_bytes ? WPOS - RPOS : n_bytes;
  for(int idx=0; idx < siz; idx += 1){
    buf[idx] = INBUF[RPOS];
    RPOS += 1;
  }
  if(RPOS == WPOS){
    MSG_AVAILABLE = false;
    WPOS = 0;
    RPOS = 0;
  }
  return siz;

}
void discard_input(int n_bytes){
  if(not MSG_AVAILABLE){
    return;
  }
  int siz = WPOS - RPOS < n_bytes ? WPOS - RPOS : n_bytes;
  RPOS += siz;
  if(RPOS == WPOS){
    MSG_AVAILABLE = false;
    WPOS = 0;
    RPOS = 0;
  }
}


int read_floats(float * data, int n){
  return get_input((byte *) data, n*4);
}

int read_bytes(uint8_t * data, int n){
  return get_input(data, n);
}

void discard_bytes(int n){
  discard_input(n);
}

uint8_t read_byte(){
  uint8_t value;
  get_input(&value, 1);
  return value;
}

}
