#include "AnalogLib.h"
#include <float.h>
#include "calib_util.h"
#include "fu.h"


profile_t Fabric::Chip::Tile::Slice::Integrator::measure(profile_spec_t spec){

  integ_code_t codes_integ = m_codes;
  m_codes = spec.codes.integ;
  switch(spec.type){
  case INTEG_INITIAL_COND:
    return measureInitialCond();
  case INTEG_DERIVATIVE_STABLE:
    return measureClosedLoopCircuit();
  case INTEG_DERIVATIVE_TC:
    return measureOpenLoopCircuit(OPENLOOP_TC);
  case INTEG_DERIVATIVE_BIAS:
    return measureOpenLoopCircuit(OPENLOOP_BIAS);
  default:
    error("integrator.measure : unknown mode");
  }
  m_codes = codes_integ;
}

profile_t Fabric::Chip::Tile::Slice::Integrator::measureClosedLoopCircuit(){
  Fabric::Chip::Tile::Slice::Fanout * fan = &this->parentSlice->fans[0];

  fanout_code_t codes_fan = fan->m_codes;
  integ_code_t codes_integ = m_codes;

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
  float in1 = 0.0;
  int mode = 1;
  util::meas_steady_chip_out(this,mean,variance);

  profile_t result = prof::make_profile(out0Id,
                                        mode,
                                        target,
                                        target,
                                        in1,
                                        mean-target,
                                        variance);

  conn_out_to_fan.brkConn();
  conn_fan0_to_in.brkConn();
  conn_fan1_to_tileout.brkConn();
  tileout_to_chipout.brkConn();
  cutil::restore_conns(calib);
  fan->update(codes_fan);
  update(codes_integ);
  return result;
}



profile_t Fabric::Chip::Tile::Slice::Integrator::measureOpenLoopCircuit(open_loop_prop_t prop){
  Dac * val_dac = parentSlice->dac;

  //save state
  integ_code_t codes_integ = m_codes;
  dac_code_t codes_val_dac = val_dac->m_codes;
  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_integ_conns(calib,this);
  cutil::buffer_dac_conns(calib,val_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile
                              ->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);
  float target_tc = Fabric::Chip::Tile::Slice
    ::Integrator::computeTimeConstant(this->m_codes);
  // configure value DAC
  float dummy;

  float input = 0.0;
  if(target_tc > 1.5*NOMINAL_TIME_CONSTANT){
    this->setInitial(0.0);
    input = val_dac->fastMakeValue(0.02);
  }
  else {
    this->setInitial(0.0);
    input = val_dac->fastMakeValue(0.20);
  }
  float expected = val_dac->computeOutput(val_dac->m_codes);
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

  const int n_samples = 25;
  float nom_times[25],k_times[25];
  float nom_values[25],k_values[25];
  conn_dac_to_in.setConn();
  print_info("=== with input ===");
  int n = util::meas_transient_chip_out(this,
                                    k_times, k_values,
                                    n_samples);
  // with ground.
  conn_dac_to_in.brkConn();
  print_info("=== without input ===");
  int m = util::meas_transient_chip_out(this,
                                        nom_times, nom_values,
                                        n_samples);

  time_constant_stats tc_stats = estimate_time_constant(input,
                                                        min(n,m),
                                                        nom_times,nom_values,
                                                        k_times,k_values);

  float in1 = 0.0;
  int mode;
  profile_t result;
  switch(prop){
  case OPENLOOP_TC:
    mode = 2;
    result = prof::make_profile(out0Id,
                                mode,
                                target_tc,
                                input,
                                in1,
                                tc_stats.tc - target_tc,
                                tc_stats.R2_k);
    break;
  case OPENLOOP_BIAS:
    mode = 3;
    result = prof::make_profile(out0Id,
                                mode,
                                0.0,
                                0.0,
                                in1,
                                tc_stats.eps,
                                tc_stats.R2_eps);
    break;
  }


  conn_out_to_tile.brkConn();
  tileout_to_chipout.brkConn();
  val_dac->update(codes_val_dac);
  cutil::restore_conns(calib);
  val_dac->update(codes_val_dac);
  update(codes_integ);
  return result;
}
profile_t Fabric::Chip::Tile::Slice::Integrator::measureInitialCond(){
  Dac * ref_dac = parentSlice->dac;
  //back up codes

  integ_code_t codes_integ = m_codes;
  dac_code_t codes_ref_dac = ref_dac->m_codes;

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

  //setInitial(input);
  float target = this->computeInitCond(m_codes);
  float mean,variance;
  bool measure_steady=false;
  calib.success &= cutil::measure_signal_robust(this,
                                                ref_dac,
                                                target,
                                                measure_steady,
                                                mean,
                                                variance);
  int mode = 0;
  float in1 = 0.0;
  float bias = (mean-target);
  profile_t prof = prof::make_profile(out0Id,
                                      mode,
                                      target,
                                      input,
                                      in1,
                                      bias,
                                      variance);
  if(!calib.success){
    prof.mode = 255;
  }
  ref_to_tile.brkConn();
  integ_to_tile.brkConn();
	tile_to_chip.brkConn();
  cutil::restore_conns(calib);
  ref_dac->update(codes_ref_dac);
  update(codes_integ);
  return prof;
}


