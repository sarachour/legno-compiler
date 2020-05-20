#include "block_state.h"
#include "profile.h"
#include "util.h"

namespace prof {

  profile_t TEMP;

  profile_t make_profile(profile_spec_t& spec,
                         float mean, float std){
    profile_t result;
    result.spec = spec;
    result.mean = mean;
    result.stdev = std;
    result.status = profile_status_t::SUCCESS;
    return result;
  }

  float * get_input(profile_spec_t& spec, port_type_t port){
    return &spec.inputs[port];
  }


}
