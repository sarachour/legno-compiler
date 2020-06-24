#ifndef CALIB_RESULT_H
#define CALIB_RESULT_H

#define VAL_DONT_CARE 0.0

namespace prof {

  extern profile_t TEMP;

  const char * profile_status_to_string(profile_status_t status);
  void sprintf_profile_spec(profile_spec_t& result, char * buf);
  void sprintf_profile(profile_t& result, char * buf);

  profile_t make_profile(profile_spec_t& spec,
                         float mean,
                         float std);
  float * get_input(profile_spec_t& spec, port_type_t port);
}
#endif
