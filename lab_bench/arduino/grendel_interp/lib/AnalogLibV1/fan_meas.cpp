#include "AnalogLib.h"
#include "assert.h"
#include "calib_util.h"


profile_t Fabric::Chip::Tile::Slice::Fanout::measure(profile_spec_t spec) {

  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice].dac;
  Dac * val_dac = parentSlice->dac;

  // save state
  cutil::calibrate_t calib;
  cutil::initialize(calib);

  fanout_code_t codes_fan = m_codes;
  dac_code_t codes_val_dac = val_dac->m_codes;
  dac_code_t codes_ref_dac = ref_dac->m_codes;

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
  case out0Id:
    Connection (out0, this->parentSlice->tileOuts[3].in0).setConn();
    break;
  case out1Id:
    Connection(out1, this->parentSlice->tileOuts[3].in0).setConn();
    break;
  case out2Id:
    setThird(true);
    Connection(out2, this->parentSlice->tileOuts[3].in0).setConn();
    break;
  default:
    error("unknown mode");
  }

  // apply profiling state


  this->m_codes = spec.code.fanout;
  float in_target = Dac::computeOutput(val_dac->m_codes);

  val_dac->setEnable(true);
  val_dac->setInv(false);
  spec.inputs[in0Id] = val_dac->fastMakeValue(spec.inputs[in0Id]);
  float out_target = Fabric::Chip::Tile::Slice::Fanout::computeOutput(this->m_codes,
                                                                spec.output,
                                                                spec.inputs[in0Id]);
  dac_to_fan.setConn();
	tile_to_chip.setConn();
  ref_to_tile.setConn();

  float mean,variance,dummy;
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
  case out0Id:
    Connection (out0, this->parentSlice->tileOuts[3].in0).brkConn();
    break;
  case out1Id:
    Connection(out2, this->parentSlice->tileOuts[3].in0).brkConn();
    break;
  case out2Id:
    setThird(false);
    Connection(out2, this->parentSlice->tileOuts[3].in0).brkConn();
    break;
  }
	setEnable (false);
  cutil::restore_conns(calib);
  this->update(codes_fan);
  val_dac->update(codes_val_dac);
  ref_dac->update(codes_ref_dac);
  return prof;
}
