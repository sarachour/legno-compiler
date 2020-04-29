#include "oscgen.h"
#include "block_state.h"

namespace oscgen {
  osc_env_t make_env(Fabric::Chip::Tile::Slice::FunctionUnit* fu){
    int next_slice = (slice_to_int(fu->parentSlice->sliceId) + 1) % 4;
    osc_env_t env;
    env.fan = &fu->parentSlice->fans[0];
    env.integ0 = fu->parentSlice->parentTile
      ->slices[next_slice].integrator;
    env.integ1 = fu->parentSlice->integrator;
    env.tile = &fu->parentSlice->tileOuts[3];
    env.chip = fu->parentSlice->parentTile->parentChip
      ->tiles[3].slices[2].chipOutput;
    env.fan_state = env.fan->m_state;
    env.integ0_state = env.integ0->m_state;
    env.integ1_state = env.integ1->m_state;
    env.configured = false;
    return env;
  }

  void restore(osc_env_t& env){
    env.integ0->m_state = env.integ0_state;
    env.integ1->m_state = env.integ1_state;
  }
  void backup(cutil::calibrate_t& calib, osc_env_t& env){
    cutil::buffer_fanout_conns(calib,env.fan);
    cutil::buffer_integ_conns(calib,env.integ0);
    cutil::buffer_integ_conns(calib,env.integ1);
    cutil::buffer_tileout_conns(calib,env.tile);
    cutil::buffer_chipout_conns(calib,env.chip);
    env.fan_state = env.fan->m_state;
    env.integ0_state = env.integ0->m_state;
    env.integ1_state = env.integ1->m_state;
  }

  void make_oscillator(osc_env_t& env){
    env.integ0->setRange(in0Id,RANGE_MED);
    env.integ0->setRange(out0Id,RANGE_MED);
    env.integ0->setInitial(0.0);
    env.integ0->m_state.nmos = 7;
    env.integ0->m_state.gain_cal = 63;
    env.integ0->update(env.integ1->m_state);

    env.integ1->setRange(in0Id,RANGE_MED);
    env.integ1->setRange(out0Id,RANGE_MED);
    env.integ1->setInitial(0.5);
    env.integ1->m_state.nmos = 7;
    env.integ1->m_state.gain_cal = 63;
    env.integ1->update(env.integ1->m_state);

    env.fan->setRange(RANGE_MED);
    env.fan->setInv(out0Id,true);
    env.fan->setInv(out1Id,false);
    env.fan->setInv(out2Id,false);
    env.fan->setThird(true);
    Fabric::Chip::Connection integ1_to_fan = Fabric::Chip::Connection (env.integ1->out0,
                                          env.fan->in0);
    Fabric::Chip::Connection integ0_to_integ1 = Fabric::Chip::Connection(env.integ0->out0,
                                             env.integ1->in0);
    Fabric::Chip::Connection fan_to_integ0 = Fabric::Chip::Connection (env.fan->out0,
                                          env.integ0->in0);

    integ1_to_fan.setConn();
    fan_to_integ0.setConn();
    integ0_to_integ1.setConn();
    env.configured = true;
  }
  float measure_oscillator_amplitude(osc_env_t& env, ifc outid, int nsamps){

    Fabric::Chip::Connection tileout_to_chipout = Fabric::Chip::Connection ( env.tile->out0,
                                                 env.chip->in0);

    if(!(outid == out0Id || outid == out1Id)){
      error("unexpected outid");
    }
    Fabric::Chip::Connection * fan_to_tileout;
    if(outid == out0Id){
      fan_to_tileout = &Fabric::Chip::Connection (
                                                 env.fan->out1,
                                                 env.tile->in0 );
    }
    else{
      fan_to_tileout = &Fabric::Chip::Connection (
                                                 env.fan->out2,
                                                 env.tile->in0 );

    }
    tileout_to_chipout.setConn();
    fan_to_tileout->setConn();
    float ampl = env.chip->analogMax(nsamps);
    tileout_to_chipout.brkConn();
    fan_to_tileout->brkConn();
    return ampl;
  }
  void teardown_oscillator(osc_env_t& env){

  }
}
