#include "profile.h"
#include "AnalogLib.h"

namespace prof {

  profile_t TEMP;

  void sprintf_profile_spec(profile_spec_t& result, char * buf){
    char BUF[256];
    sprintf_block_state()
    sprintf(FMTBUF, "profile-spec state=%s in(%f,%f) out=%s type=%s",
            BUF)
  }
  void sprintf_profile(profile_t& result, char * buf){
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
  profile_t make_profile(profile_spec_t& spec,
                         float mean, float std){
    profile_t result;
    result.spec = spec;
    result.mean = mean;
    result.std = std;
    result.status = profile_status_t::SUCCESS;
    return result;
  }



}
