#include "AnalogLib.h"
#include "assert.h"
#include "calib_util.h"
#include "emulator.h"

emulator::physical_model_t draw_random_model(profile_spec_t spec){
  emulator::physical_model_t model;
  emulator::ideal(model);
  Fabric::Chip::Tile::Slice::Fanout::computeInterval(spec.state.fanout,
                                                      in0Id,
                                                      model.in0.min,
                                                      model.in0.max);
  emulator::bound(model.in1,-1,1);
  return model;
 

}
profile_t Fabric::Chip::Tile::Slice::Fanout::measure(profile_spec_t spec) {
#ifdef EMULATE_HARDWARE
  sprintf(FMTBUF,"measured value: in=(%f,%f)\n", spec.inputs[0],spec.inputs[1]);
  print_info(FMTBUF);

  float std;
  float * input = prof::get_input(spec,port_type_t::in0Id);
  float output = Fabric::Chip::Tile::Slice::Fanout::computeOutput(spec.state.fanout,
                                                                  spec.output,
                                                                  *input);

  emulator::physical_model_t model = draw_random_model(spec);
  float result = emulator::draw(model,*input,0.0,output,std);
  sprintf(FMTBUF,"output=%f result=%f\n", output,result);
  print_info(FMTBUF);
  profile_t prof = prof::make_profile(spec, result,
                                      std);
  return prof;

#else
  return this->measureConstVal(spec);
#endif
}

profile_t Fabric::Chip::Tile::Slice::Fanout::measureConstVal(profile_spec_t spec) {

  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice].dac;
  Dac * val_dac = parentSlice->dac;

  // save state
  cutil::calibrate_t calib;
  cutil::initialize(calib);

  fanout_state_t codes_fan = this->m_state;
  dac_state_t codes_val_dac = val_dac->m_state;
  dac_state_t codes_ref_dac = ref_dac->m_state;
  float * input_value = prof::get_input(spec,port_type_t::in0Id);

  cutil::buffer_fanout_conns(calib,this);
  cutil::buffer_dac_conns(calib,ref_dac);
  cutil::buffer_dac_conns(calib,val_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,
                              parentSlice->parentTile->parentChip
                              ->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);


  Connection dac_to_fan = Connection ( val_dac->out0, in0 );
  Connection tile_to_chip = Connection (parentSlice->tileOuts[3].out0,
                                parentSlice->parentTile->parentChip \
                                ->tiles[3].slices[2].chipOutput->in0);
  Connection ref_to_tile = Connection ( ref_dac->out0,
                                        parentSlice->tileOuts[3].in0 );

  switch(spec.output){
  case port_type_t::out0Id:
    Connection (out0, this->parentSlice->tileOuts[3].in0).setConn();
    break;
  case port_type_t::out1Id:
    Connection(out1, this->parentSlice->tileOuts[3].in0).setConn();
    break;
  case port_type_t::out2Id:
    setThird(true);
    Connection(out2, this->parentSlice->tileOuts[3].in0).setConn();
    break;
  default:
    sprintf(FMTBUF,"unknown output <%s>", port_type_to_string(spec.output));
    error(FMTBUF);

  }

  // apply profiling state


  this->m_state= spec.state.fanout;
  //float in_target = Dac::computeOutput(val_dac->m_state);

  val_dac->setEnable(true);
  val_dac->setInv(false);
  *input_value = val_dac->fastMakeValue(*input_value);
  float out_target = Fabric::Chip::Tile::Slice::Fanout::computeOutput(this->m_state,
                                                                     spec.output,
                                                                      *input_value);
  dac_to_fan.setConn();
	tile_to_chip.setConn();
  ref_to_tile.setConn();

  float mean,variance;
  bool measure_steady_state = false;
  calib.success &= cutil::measure_signal_robust(this,
                                                ref_dac,
                                                out_target,
                                                measure_steady_state,
                                                mean,
                                                variance);

  sprintf(FMTBUF,"PARS mean=%f variance=%f",
          mean,variance);
  print_info(FMTBUF);
  profile_t prof = prof::make_profile(spec, mean,
                                      sqrt(variance));
  if(!calib.success){
    prof.status = profile_status_t::FAILED_TO_CALIBRATE;
  }
  dac_to_fan.brkConn();
  tile_to_chip.brkConn();
  ref_to_tile.brkConn();
  switch(spec.output){
  case port_type_t::out0Id:
    Connection (out0, this->parentSlice->tileOuts[3].in0).brkConn();
    break;
  case port_type_t::out1Id:
    Connection(out1, this->parentSlice->tileOuts[3].in0).brkConn();
    break;
  case port_type_t::out2Id:
    setThird(false);
    Connection(out2, this->parentSlice->tileOuts[3].in0).brkConn();
    break;
  default:
    sprintf(FMTBUF,"unknown output <%s>", port_type_to_string(spec.output));
    error(FMTBUF);

  }
	setEnable (false);
  cutil::restore_conns(calib);
  this->update(codes_fan);
  val_dac->update(codes_val_dac);
  ref_dac->update(codes_ref_dac);
  return prof;
}
