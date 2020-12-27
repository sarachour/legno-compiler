#include "AnalogLib.h"
#include <float.h>
#include "calib_util.h"
#include "fu.h"
#include "emulator.h"

#define DEBUG_INTEG_PROF
emulator::physical_model_t integ_draw_random_model(profile_spec_t spec){
  emulator::physical_model_t model;
  emulator::ideal(model);
  Fabric::Chip::Tile::Slice::Multiplier::computeInterval(spec.state.mult,
                                                         in0Id,
                                                         model.in0.min,
                                                         model.in0.max);

  return model;
}



profile_t Fabric::Chip::Tile::Slice::Integrator::measure(profile_spec_t spec){

#ifdef EMULATE_HARDWARE
  emulator::physical_model_t model = integ_draw_random_model(spec);
  float * input0 = prof::get_input(spec,port_type_t::in0Id);
  float output = 0.0;
  switch(spec.type){
  case INTEG_INITIAL_COND:
    output = Fabric::Chip::Tile::Slice::Integrator::computeInitCond(spec.state.integ);
    break;
  case INTEG_DERIVATIVE_STABLE:
    output = 0.0;
    break;
  case INTEG_DERIVATIVE_GAIN:
    output = 1.0;
    break;
  case INTEG_DERIVATIVE_BIAS:
    output = 0.0;
    break;
  default:
    error("not expected");
  }
  float std;
  //float result = emulator::draw(model,*input0,1.0,output,std);
  float result = output;
  sprintf(FMTBUF,"output=%f result=%f\n", output,result);
  print_info(FMTBUF);
  profile_t prof = prof::make_profile(spec, result,
                                      std);
  return prof;

#else
  integ_state_t state_integ = this->m_state;
  profile_t dummy;
  this->m_state= spec.state.integ;
  switch(spec.type){
  case INTEG_INITIAL_COND:
    return measureInitialCond(spec);
  case INTEG_DERIVATIVE_STABLE:
    return measureClosedLoopCircuit(spec);
  case INTEG_DERIVATIVE_GAIN:
  case INTEG_DERIVATIVE_BIAS:
    return measureOpenLoopCircuit(spec);
  case INPUT_OUTPUT:
    error("integrator.measure : input-output measurements not supported");
  default:
    sprintf(FMTBUF, "integrator.measure : unknown mode %d", spec.type);
    error(FMTBUF);
  }
  this->m_state = state_integ;
  return dummy;
#endif
}

profile_t Fabric::Chip::Tile::Slice::Integrator::measureClosedLoopCircuit(profile_spec_t spec){
  Fabric::Chip::Tile::Slice::Fanout * fan = &this->parentSlice->fans[0];

  fanout_state_t state_fan = fan->m_state;
  integ_state_t state_integ = this->m_state;

  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_fanout_conns(calib,fan);
  cutil::buffer_integ_conns(calib,this);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,
                              parentSlice->parentTile->parentChip
                              ->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);


  float out0bias, out1bias, out2bias;
  fan->setRange(RANGE_MED);
  fan->setInv(out0Id,true);
  fan->setInv(out1Id,false);
  fan->setInv(out2Id,false);
  fan->measureZero(out0bias,out1bias,out2bias);
  float target = 0.0 + out0bias + out1bias;

  sprintf(FMTBUF,"fan bias0=%f bias1=%f bias2=%f", out0bias,out1bias,out2bias);
  print_info(FMTBUF);
  // configure init cond
  setInitial(0.0);

  // create open loop circuits
  Connection conn_out_to_fan = Connection (this->out0,fan->in0);
  Connection conn_fan0_to_in = Connection (fan->out0, this->in0);
  Connection conn_fan1_to_tileout = Connection (fan->out1,
                                                parentSlice->tileOuts[3].in0);
  Connection tileout_to_chipout = Connection (parentSlice->tileOuts[3].out0,
                                              parentSlice->parentTile->parentChip
                                              ->tiles[3].slices[2].chipOutput->in0);


  conn_out_to_fan.setConn();
  conn_fan0_to_in.setConn();
  conn_fan1_to_tileout.setConn();
  tileout_to_chipout.setConn();

  float mean, variance;
  util::meas_steady_chip_out(this,mean,variance);

  profile_t result = prof::make_profile(spec,
                                        mean-target,
                                        variance);

  conn_out_to_fan.brkConn();
  conn_fan0_to_in.brkConn();
  conn_fan1_to_tileout.brkConn();
  tileout_to_chipout.brkConn();
  cutil::restore_conns(calib);
  fan->update(state_fan);
  update(state_integ);
  return result;
}



profile_t Fabric::Chip::Tile::Slice::Integrator::measureOpenLoopCircuit(profile_spec_t spec){
  Dac * val_dac = parentSlice->dac;

  //save state
  integ_state_t state_integ = m_state;
  dac_state_t state_val_dac = val_dac->m_state;
  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_integ_conns(calib,this);
  cutil::buffer_dac_conns(calib,val_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile
                              ->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);
  float target_tc = Fabric::Chip::Tile::Slice
    ::Integrator::computeTimeConstant(this->m_state) / NOMINAL_TIME_CONSTANT;
  // configure value DAC

  float input = 0.0;
  if(target_tc > 1.5){
    this->setInitial(0.0);
    input = val_dac->fastMakeValue(0.02);
  }
  else {
    this->setInitial(0.0);
    input = val_dac->fastMakeValue(0.20);
  }
  float expected = val_dac->computeOutput(val_dac->m_state);
  sprintf(FMTBUF,"open-loop input=%f expected=%f",input,expected);
  print_info(FMTBUF);

  // set the initial condition of the system
 // build open loop circuit
  Connection conn_out_to_tile = Connection (this->out0,parentSlice->tileOuts[3].in0);
  Connection conn_dac_to_in = Connection (val_dac->out0, this->in0);
  Connection tileout_to_chipout = Connection (parentSlice->tileOuts[3].out0,
                                              parentSlice->parentTile->parentChip
                                              ->tiles[3].slices[2].chipOutput->in0);
  conn_out_to_tile.setConn();
  tileout_to_chipout.setConn();

  const int npts = 10;
  float values[10];

  for(int i=0; i < 10; i + 1){
    const int n_samples = 25;
    float nom_times[25],k_times[25];
    float nom_values[25],k_values[25];

    conn_dac_to_in.setConn();
    int n = util::meas_transient_chip_out(this,
                                      k_times, k_values,
                                      n_samples);
    // with ground.
    conn_dac_to_in.brkConn();
    int m = util::meas_transient_chip_out(this,
                                          nom_times, nom_values,
                                          n_samples);

    time_constant_stats tc_stats = estimate_time_constant(input,
                                                          min(n,m),
                                                          nom_times,nom_values,
                                                          k_times,k_values);
    switch(spec.type){
    case INTEG_DERIVATIVE_GAIN:
      values[i] = (float) tc_stats.tc/NOMINAL_TIME_CONSTANT;
      break;
    case INTEG_DERIVATIVE_BIAS:
      values[i] = (float) tc_stats.eps;
      break;
    default:
      error("unexpected profile-spec type");
      break;
    }
  }
  float mean,variance;
  profile_t result;

  util::distribution(values,npts,mean,variance);
  result = prof::make_profile(spec, mean, sqrt(variance));

#ifdef DEBUG_INTEG_PROF
  switch(spec.type){
  case INTEG_DERIVATIVE_GAIN:
    sprintf(FMTBUF,"prof-integ-gain targ=%f meas=%f std=%f\n",
            target_tc, mean, sqrt(variance));
    print_info(FMTBUF);
    break;
  case INTEG_DERIVATIVE_BIAS:
    sprintf(FMTBUF,"prof-integ-offset targ=%f meas=%f std=%f\n",
            0.0, mean, sqrt(variance));
    print_info(FMTBUF);
    break;
  default:
    error("unexpected profile-spec type");
    break;
  }
#endif

  conn_out_to_tile.brkConn();
  tileout_to_chipout.brkConn();
  val_dac->update(state_val_dac);
  cutil::restore_conns(calib);
  val_dac->update(state_val_dac);
  update(state_integ);
  return result;
}
profile_t Fabric::Chip::Tile::Slice::Integrator::measureInitialCond(profile_spec_t spec){
  Dac * ref_dac = parentSlice->dac;
  //back up codes

  integ_state_t state_integ = this->m_state;
  dac_state_t state_ref_dac = ref_dac->m_state;

  cutil::calibrate_t calib;
  cutil::initialize(calib);

  cutil::buffer_integ_conns(calib,this);
  cutil::buffer_dac_conns(calib,ref_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile
                              ->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

  Connection ref_to_tile = Connection ( ref_dac->out0,
                                        parentSlice->tileOuts[3].in0 );
  //conn2
	Connection integ_to_tile= Connection ( out0,
                                         parentSlice->tileOuts[3].in0 );
	Connection tile_to_chip = Connection ( parentSlice->tileOuts[3].out0,
                                         parentSlice->parentTile
                                         ->parentChip->tiles[3].slices[2].chipOutput->in0 );
  ref_to_tile.setConn();
  integ_to_tile.setConn();
	tile_to_chip.setConn();

  float target = this->computeInitCond(m_state);
  float mean,variance;
  bool measure_steady=false;
  this->update(this->m_state);
  calib.success &= cutil::measure_signal_robust(this,
                                                ref_dac,
                                                target,
                                                measure_steady,
                                                mean,
                                                variance);
#ifdef DEBUG_INTEG_PROF
  sprintf(FMTBUF,"prof-integ-ic inp=%f target=%f mean=%f\n",
          spec.inputs[in0Id],target,mean);
  print_info(FMTBUF);
#endif

  profile_t prof = prof::make_profile(spec,
                                      mean,
                                      variance);
  if(!calib.success){
    prof.status = FAILED_TO_CALIBRATE;
  }
  ref_to_tile.brkConn();
  integ_to_tile.brkConn();
	tile_to_chip.brkConn();
  cutil::restore_conns(calib);
  ref_dac->update(state_ref_dac);
  update(state_integ);
  return prof;
}


