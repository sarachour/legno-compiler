#include "AnalogLib.h"
#include "fu.h"
#include "calib_util.h"
#include "profile.h"
#include "oscgen.h"
#include "emulator.h"
#include <float.h>

emulator::physical_model_t mult_draw_random_model(profile_spec_t spec){
  emulator::physical_model_t model;
  emulator::ideal(model);
  Fabric::Chip::Tile::Slice::Multiplier::computeInterval(spec.state.mult,
                                                     in0Id,
                                                     model.in0.min,
                                                     model.in0.max);
  Fabric::Chip::Tile::Slice::Multiplier::computeInterval(spec.state.mult,
                                                         in1Id,
                                                         model.in1.min,
                                                         model.in1.max);

  return model;
}

profile_t Fabric::Chip::Tile::Slice::Multiplier::measure(profile_spec_t spec) {
#ifdef EMULATE_HARDWARE
  float gain_val = (spec.state.mult.gain_code - 128.0)/128.0;
  float std;
  float * input0 = prof::get_input(spec,port_type_t::in0Id);
  float * input1 = prof::get_input(spec,port_type_t::in1Id);
  float output = Fabric::Chip::Tile::Slice::Multiplier::computeOutput(spec.state.mult,
                                                                      *input0,
                                                                      *input1);
  sprintf(FMTBUF,"inputs in=(%f,%f) gain=%f out=%f\n",  \
          spec.inputs[0], \
          spec.inputs[1], \
          gain_val, output);
  print_info(FMTBUF);

  emulator::physical_model_t model = mult_draw_random_model(spec);
  float result = emulator::draw(model,*input0,*input1,output,std);
  sprintf(FMTBUF,"output=%f result=%f\n", output,result);
  print_info(FMTBUF);
  profile_t prof = prof::make_profile(spec, result,
                                      std);
  return prof;

#else
  mult_state_t backup = m_state;
  this->m_state = spec.state.mult;
  profile_t result = result;
  if(this->m_state.vga){
    result = measureVga(spec);
  }
  else{
    result = measureMult(spec);
  }
  this->m_state = backup;
  return result;
#endif
}

profile_t Fabric::Chip::Tile::Slice::Multiplier::measureVga(profile_spec_t spec) {
  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice].dac;
  Dac * val1_dac = parentSlice->dac;

  cutil::calibrate_t calib;
  cutil::initialize(calib);
  // backup state of each component that will be clobbered
  mult_state_t state_mult = this->m_state;
  dac_state_t state_val1 = val1_dac->m_state;
  dac_state_t state_ref = ref_dac->m_state;

  // backup connections
  cutil::buffer_mult_conns(calib,this);
  cutil::buffer_dac_conns(calib,ref_dac);
  cutil::buffer_dac_conns(calib,val1_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile
                              ->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);


  Connection dac_to_in0 = Connection(val1_dac->out0, in0);
  Connection mult_to_tileout = Connection ( out0, parentSlice->tileOuts[3].in0 );
  Connection tileout_to_chipout = Connection ( parentSlice->tileOuts[3].out0,
                                               parentSlice->parentTile
                                               ->parentChip->tiles[3].slices[2].chipOutput->in0 );
  Connection ref_to_tileout = Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0 );

  spec.inputs[in0Id]= val1_dac->fastMakeValue(spec.inputs[in0Id]);
  float target_vga = computeOutput(this->m_state,
                                   spec.inputs[in0Id], 
                                   VAL_DONT_CARE);
  if(fabs(target_vga) > 10.0){
    sprintf(FMTBUF, "can't fit %f", target_vga);
    calib.success = false;
  }

  dac_to_in0.setConn();
  mult_to_tileout.setConn();
  tileout_to_chipout.setConn();
  ref_to_tileout.setConn();
  float mean,variance;
  const bool meas_steady = false;
  if(calib.success){
    calib.success &= cutil::measure_signal_robust(this,
                                                  ref_dac,
                                                  target_vga,
                                                  meas_steady,
                                                  mean,
                                                  variance);
  }
  print_info(FMTBUF);
  profile_t prof = prof::make_profile(spec,
                                      mean,
                                      sqrt(variance));
  if(!calib.success){
    prof.status = FAILED_TO_CALIBRATE;
  }
  dac_to_in0.brkConn();
  mult_to_tileout.brkConn();
  tileout_to_chipout.brkConn();
  ref_to_tileout.brkConn();
  cutil::restore_conns(calib);
  ref_dac->update(state_ref);
  val1_dac->update(state_val1);
  this->update(state_mult);
  return prof;

}


profile_t Fabric::Chip::Tile::Slice::Multiplier::measureMult(profile_spec_t spec) {
  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  int next2_slice = (slice_to_int(parentSlice->sliceId) + 2) % 4;
  Dac * val2_dac = parentSlice->parentTile->slices[next_slice].dac;
  Dac * val1_dac = parentSlice->dac;
  Dac * ref_dac = parentSlice->parentTile->slices[next2_slice].dac;

  cutil::calibrate_t calib;
  cutil::initialize(calib);
  // backup state of each component that will be clobbered
  mult_state_t state_self = m_state;
  dac_state_t state_val1 = val1_dac->m_state;
  dac_state_t state_val2 = val2_dac->m_state;
  dac_state_t state_ref = ref_dac->m_state;

  // backup connections
  cutil::buffer_mult_conns(calib,this);
  cutil::buffer_dac_conns(calib,ref_dac);
  cutil::buffer_dac_conns(calib,val1_dac);
  cutil::buffer_dac_conns(calib,val2_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);


  Connection dac_to_in0 = Connection(val1_dac->out0, in0);
  Connection dac_to_in1 = Connection(val2_dac->out0, in1);
  Connection mult_to_tileout = Connection ( out0, parentSlice->tileOuts[3].in0 );
	Connection tileout_to_chipout = Connection ( parentSlice->tileOuts[3].out0,
                                               parentSlice->parentTile->parentChip->tiles[3].slices[2].chipOutput->in0 );
  Fabric::Chip::Connection ref_to_tileout =
    Fabric::Chip::Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0 );


  dac_to_in0.setConn();
  dac_to_in1.setConn();
  mult_to_tileout.setConn();
  tileout_to_chipout.setConn();
  ref_to_tileout.setConn();


  float target_in0 = val1_dac->fastMakeValue(spec.inputs[in0Id]);
  float target_in1 = val2_dac->fastMakeValue(spec.inputs[in1Id]);
  float target_mult = computeOutput(m_state,target_in0,target_in1);
  if(fabs(target_mult) > 10.0){
    calib.success = false;
  }
  float mean,variance;
  const bool meas_steady;
  if(calib.success){
    calib.success &= cutil::measure_signal_robust(this,
                                                  ref_dac,
                                                  target_mult,
                                                  meas_steady,
                                                  mean,
                                                  variance);

  }
  profile_t prof = prof::make_profile(spec,
                                      mean,
                                      sqrt(variance));

  if(!calib.success){
    prof.status = FAILED_TO_CALIBRATE;
  }
  dac_to_in0.brkConn();
  dac_to_in1.brkConn();
  mult_to_tileout.brkConn();
  tileout_to_chipout.brkConn();
  ref_to_tileout.brkConn();
  cutil::restore_conns(calib);
  ref_dac->update(state_ref);
  val1_dac->update(state_val1);
  val2_dac->update(state_val2);
  this->update(state_self);
  return prof;
}
