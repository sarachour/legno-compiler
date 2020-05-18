#include "AnalogLib.h"
#include "calib_util.h"
#include "profile.h"
#ifndef CALIBRATE_H
#define CALIBRATE_H

namespace calibrate {
  profile_t measure(Fabric * fab,
                    profile_spec_t& spec);


  void calibrate(Fabric * fab,
                 block_loc_t loc,
                 calib_objective_t obj);


  void get_state(Fabric * fab,
                 block_loc_t loc,
                 block_state_t& buf);

  void set_state(Fabric * fab,
                 block_loc_t loc,
                 block_state_t& buf);

}

#endif
