#ifndef CALIB_RESULT_H
#define CALIB_RESULT_H


#include "float16.h"



namespace prof {

  extern profile_t TEMP;

  void print_profile_spec(profile_spec_t& result, int level);
  void print_profile(profile_t& result, int level);

  profile_t make_profile(profile_spec_t& spec,
                         float mean,
                         float std);
}
#endif
