#include "AnalogLib.h"
#include "fu.h"
#include "calib_util.h"
#include "profile.h"
#include "oscgen.h"
#include <float.h>

profile_t Fabric::Chip::Tile::Slice::Multiplier::measure(int mode,float in0val,float in1val) {
  if(mode == 0){
    if(this->m_codes.vga){
      return measureVga(in0val,in1val);
    }
    else{
      return measureMult(in0val,in1val);
    }
  }
  else {
    error("unknown mode");
  }
}

profile_t Fabric::Chip::Tile::Slice::Multiplier::measureVga(float normalized_in0val,float gain) {
  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice].dac;
  Dac * val1_dac = parentSlice->dac;

  cutil::calibrate_t calib;
  cutil::initialize(calib);
  // backup state of each component that will be clobbered
  mult_code_t codes_mult = m_codes;
  dac_code_t codes_val1 = val1_dac->m_codes;
  dac_code_t codes_ref = ref_dac->m_codes;

  setGain(gain);
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

  float in0val = util::range_to_coeff(this->m_codes.range[in0Id])*(normalized_in0val);
  float target_in0 = val1_dac->fastMakeValue(in0val);
  float target_vga = computeOutput(this->m_codes,
                                   target_in0,
                                   0.0);
  if(fabs(target_vga) > 10.0){
    sprintf(FMTBUF, "can't fit %f", target_vga);
    calib.success = false;
  }

  dac_to_in0.setConn();
  mult_to_tileout.setConn();
  tileout_to_chipout.setConn();
  ref_to_tileout.setConn();
  float mean,variance;
  float target_gain = (m_codes.gain_code-128.0)/128.0;
  bool meas_steady = false;
  if(calib.success){
    calib.success &= cutil::measure_signal_robust(this,
                                                  ref_dac,
                                                  target_vga,
                                                  meas_steady,
                                                  mean,
                                                  variance);
  }
  float bias = (mean-target_vga);
  sprintf(FMTBUF,"PARS input=%f/%f gain=%f/%f target=%f meas=%f",
          in0val,target_in0,gain,target_gain,
          target_vga,mean);
  print_info(FMTBUF);
  const int mode = 0;
  profile_t prof = prof::make_profile(out0Id,
                                      mode,
                                      target_vga,
                                      target_in0,
                                      gain,
                                      bias,
                                      variance);
  if(!calib.success){
    prof.mode = 255;
  }
  dac_to_in0.brkConn();
  mult_to_tileout.brkConn();
  tileout_to_chipout.brkConn();
  ref_to_tileout.brkConn();
  cutil::restore_conns(calib);
  ref_dac->update(codes_ref);
  val1_dac->update(codes_val1);
  this->update(codes_mult);
  return prof;

}


profile_t Fabric::Chip::Tile::Slice::Multiplier::measureMult(float normalized_in0val,
                                                             float normalized_in1val) {
  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  int next2_slice = (slice_to_int(parentSlice->sliceId) + 2) % 4;
  Dac * val2_dac = parentSlice->parentTile->slices[next_slice].dac;
  Dac * val1_dac = parentSlice->dac;
  Dac * ref_dac = parentSlice->parentTile->slices[next2_slice].dac;

  cutil::calibrate_t calib;
  cutil::initialize(calib);
  // backup state of each component that will be clobbered
  mult_code_t codes_self = m_codes;
  dac_code_t codes_val1 = val1_dac->m_codes;
  dac_code_t codes_val2 = val2_dac->m_codes;
  dac_code_t codes_ref = ref_dac->m_codes;

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


  float in0val = util::range_to_coeff(this->m_codes.range[in0Id])*(normalized_in0val);
  float in1val = util::range_to_coeff(this->m_codes.range[in1Id])*(normalized_in1val);
  float target_in0 = val1_dac->fastMakeValue(in0val);
  float target_in1 = val2_dac->fastMakeValue(in1val);
  float target_mult = computeOutput(m_codes,target_in0,target_in1);
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
  sprintf(FMTBUF,"config inps=(%f,%f) in0=%f in1=%f output=%f meas=%f",
          in0val,in1val,target_in0,target_in1,target_mult,mean);
  print_info(FMTBUF);

  float bias = mean-target_mult;
  const int mode = 0;
  profile_t prof = prof::make_profile(out0Id,
                                      mode,
                                      target_mult,
                                      target_in0,
                                      target_in1,
                                      bias,
                                      variance);

  if(!calib.success){
    prof.mode = 255;
  }
  dac_to_in0.brkConn();
  dac_to_in1.brkConn();
  mult_to_tileout.brkConn();
  tileout_to_chipout.brkConn();
  ref_to_tileout.brkConn();
  cutil::restore_conns(calib);
  ref_dac->update(codes_ref);
  val1_dac->update(codes_val1);
  val2_dac->update(codes_val2);
  this->update(codes_self);
  return prof;
}
