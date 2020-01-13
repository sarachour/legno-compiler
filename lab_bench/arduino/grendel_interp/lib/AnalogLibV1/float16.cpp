#include "float16.h"

namespace float16 {
  uint16_t zero(){
    return 0;
  };

  uint16_t from_float32(float f)
  {
    uint16_t val = 0;
    if(f == 0) {
      val=0;
      return;
    }

    const unsigned long int ff=*reinterpret_cast<unsigned long int*>(&f);

    // extract exponent and mantissa from the float
    const uint8_t fexp(((ff&0x7FFFFFFF)>>23)-127);
    const unsigned long int mant=ff&0x007FFFFF;

    /*
    Serial.print("floating is ");
    Serial.println(ff,HEX);
    Serial.print("exponent is ");
    Serial.println(fexp,DEC);
    Serial.print("mantissa is ");
    Serial.println(mant,HEX);
    */

    const uint16_t bias = (1<<(nbits_exp-1))-1;
    /*
    Serial.print("new bias is ");
    Serial.println(bias,DEC);
    */
    const uint16_t newexp = ((fexp+bias)&(0xFFFF>>(16-nbits_exp)));
    /*
    Serial.print("newexp is ");
    Serial.println(newexp,HEX);
    */

    // new mantissa is just the 16-nbits_exp-1 most significant bits of the old
    const uint16_t newmant=(mant>>(23-(16-nbits_exp-1)));

    /*
    Serial.print("newmant is ");
    Serial.println(newmant,HEX);
    */

    // construct new number
    val = newmant | (newexp<<(15-nbits_exp)) | ((ff>>31)<<15);
    /*
    Serial.print("float16 is ");
    Serial.println(val,HEX);

    // test it
    float fff=float(*this);

    Serial.print("Difference is ");
    Serial.println(f/fff);
    */
    return val;
  }

  float to_float32(uint16_t val)
  {
    if(val==0)
      return 0.0f;

    // extract sign bit
    unsigned long int ff = val&0x8000;
    // and shift it up
    ff <<= 16;
    // shift up exponent so it's the least significant bits of the
    // 32-bit exp
    const long int oldexp=((val&0x7FFF)>>(15-nbits_exp));
    /*
    Serial.print("exp is ");
    Serial.println(oldexp,HEX);
    */
    const uint16_t bias = (1<<(nbits_exp-1))-1;
    ff |= ((oldexp-bias+127)<<23);

    // shift mantissa up so it's the most significant bits of the 32-bit
    // mantissa
    const uint32_t mantissa_mask=(0xFFFF>>(nbits_exp+1));
    ff |= ((val&mantissa_mask)<<(23-(15-nbits_exp)));

    const float f= *reinterpret_cast<float*>(&ff);
    /*
    Serial.print("backconverted float is ");
    Serial.println(f);
    */

    return f;
  }

}
