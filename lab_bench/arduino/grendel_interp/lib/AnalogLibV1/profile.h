#ifndef CALIB_RESULT_H
#define CALIB_RESULT_H


#include "float16.h"


typedef struct {
  float bias;
  float noise;
  float target;
  float input0;
  float input1;
  uint8_t port;
  uint8_t mode;
} profile_t;

typedef union {
  profile_t result;
  unsigned char charbuf[sizeof(profile_t)];
} serializable_profile_t;

namespace prof {

  extern profile_t TEMP;

  void print_profile(profile_t& result, int level);

  profile_t make_profile(unsigned char prop,
                         unsigned char mode,
                         float target,
                         float input0,
                         float input1,
                         float bias,
                         float noise);
}
#endif
