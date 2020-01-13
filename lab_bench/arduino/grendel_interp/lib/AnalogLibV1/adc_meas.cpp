#include "AnalogLib.h"
#include "assert.h"
#include "fu.h"
#include "calib_util.h"



float compute_in_adc(adc_code_t& m_codes,float target_input){
  float coeff = util::range_to_coeff(m_codes.range);
  return coeff*target_input;
}
float compute_out_adc(adc_code_t& m_codes,float target_input){

}
profile_t Fabric::Chip::Tile::Slice::ChipAdc::measure(float input){
  update(m_codes);

  Fabric::Chip::Tile::Slice::Dac * val_dac = parentSlice->dac;
  Fabric* fab = parentSlice->parentTile->parentChip->parentFabric;
  adc_code_t codes_self= m_codes;
  dac_code_t codes_dac = val_dac->m_codes;

  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_dac_conns(calib,val_dac);
  cutil::buffer_adc_conns(calib,this);
  cutil::break_conns(calib);

  Connection conn0 = Connection ( val_dac->out0, in0 );
	conn0.setConn();
	setEnable (true);
  val_dac->setEnable(true);
  val_dac->setRange(this->m_codes.range);
  val_dac->setInv(false);
  val_dac->setConstant(input);
  float target_input = Fabric::Chip::Tile::Slice::Dac::computeOutput(val_dac->m_codes);
  target_input = val_dac->fastMakeValue(target_input);
  float target_output = computeOutput(m_codes,target_input);

  float mean,variance;
  util::meas_dist_adc(this,mean,variance);
  const int mode = 0;
  const int in1 = 0.0;
  profile_t prof = prof::make_profile(out0Id,
                                      mode,
                                      target_output,
                                      target_input,
                                      in1,
                                      mean-target_output,
                                      variance);

  sprintf(FMTBUF, "MEAS target=%f input=%f / mean=%f var=%f",
          target_output, input, mean, variance);
  print_log(FMTBUF);
	conn0.brkConn();
	val_dac->setEnable(false);

  cutil::restore_conns(calib);
  val_dac->update(codes_dac);
  return prof;
}
