#ifndef COMM_H
#define COMM_H
#include <Arduino.h>

namespace comm {

void test(bool result, const char * error_msg);
void print_header();
void done_command();
void listen_command();
void process_command();
void response(const char* data, int ndata);
void data(const char* msg, const char * type);
void payload();
void error(const char* msg);

void* get_data_ptr(int offset);
void print_data(int offset);
int read_bytes(uint8_t * data, int n);
int read_floats(float * data, int n);
uint8_t read_byte();
void discard_bytes(int n);
void listen();
bool read_mode();
void reset();
int write_pos();
}
#endif
