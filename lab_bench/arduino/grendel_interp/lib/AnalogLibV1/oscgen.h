#include "AnalogLib.h"


namespace oscgen {


  typedef struct {
    /*the blocks involved in making the oscillator*/
    Fabric::Chip::Tile::Slice::Integrator* integ1;
    Fabric::Chip::Tile::Slice::Integrator* integ0;
    Fabric::Chip::Tile::Slice::Fanout* fan;
    Fabric::Chip::Tile::Slice::TileInOut* tile;
    Fabric::Chip::Tile::Slice::ChipOutput * chip;
    integ_state_t integ0_state;
    integ_state_t integ1_state;
    fanout_state_t fan_state;
    bool configured;
  } osc_env_t;

  osc_env_t make_env(Fabric::Chip::Tile::Slice::FunctionUnit* fu);
  void make_oscillator(osc_env_t& env);
  void backup(cutil::calibrate_t& calib, osc_env_t& env);
  void restore(osc_env_t& env);
  float measure_oscillator_amplitude(osc_env_t& env, ifc outid,int nsamps);
  void teardown_oscillator(osc_env_t& env);
}
