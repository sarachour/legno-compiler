#ifndef __float16__
#define __float16__

#include <inttypes.h>

/* The float16 class is a simple implementation of something
   float-like that only takes up 2 bytes. The number of bits in the
   exponent is settable using nbits_exp, the remaining bits are used
   up for one sign bit and the mantissa.  This can be used in
   memory-constrained situations when we don't need a full float.
*/

namespace float16 {
  static const int nbits_exp=6;
  uint16_t zero();
  uint16_t from_float32(float value);
  float to_float32(uint16_t value);
};

#endif
