#include "profile.h"
#include "AnalogLib.h"

namespace prof {

  profile_t TEMP;

  void print_profile(profile_t& result, int level){
    sprintf(FMTBUF,
            "port=%s mode=%d out=%f in0=%f in1=%f bias=%f noise=%f",
            result.port,
            result.mode,
            result.target,
            result.input0,
            result.input1,
            result.bias,
            result.noise
            );

  }
  profile_t make_profile(unsigned char prop,
                    unsigned char mode,
                    float target, float in0, float in1,
                    float bias, float noise){
    profile_t result;
    result.port = prop;
    result.mode = mode;
    result.bias = bias;
    result.noise = noise;
    result.target = target;
    result.input0 = in0;
    result.input1 = in1;
    sprintf(FMTBUF, "prof prop=%d mode=%d bias=%f noise=%f out=%f in0=%f in1=%f",
            prop,mode,bias,noise,target,in0,in1);
    print_log(FMTBUF);
    return result;
  }



}
