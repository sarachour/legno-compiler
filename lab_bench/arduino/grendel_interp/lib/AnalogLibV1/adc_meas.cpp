#include "AnalogLib.h"
#include "assert.h"
#include "fu.h"
#include "calib_util.h"




profile_t Fabric::Chip::Tile::Slice::ChipAdc::measure(profile_spec_t spec){
  update(this->m_state);

  Fabric::Chip::Tile::Slice::Dac * val_dac = parentSlice->dac;
  Fabric* fab = parentSlice->parentTile->parentChip->parentFabric;
  adc_state_t codes_self= this->m_state;
  dac_state_t codes_dac = val_dac->m_state;

  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_dac_conns(calib,val_dac);
  cutil::buffer_adc_conns(calib,this);
  cutil::break_conns(calib);

  Connection conn0 = Connection ( val_dac->out0, in0 );
	conn0.setConn();
	val_dac->setEnable (true);
  spec.inputs[in0Id] = val_dac->fastMakeValue(spec.inputs[in0Id]);

  float mean,variance;
  util::meas_dist_adc(this,mean,variance);
  const int mode = 0;
  const int in1 = 0.0;
  profile_t prof = prof::make_profile(spec,
                                      mean,
                                      variance);

	conn0.brkConn();
	val_dac->setEnable(false);

  cutil::restore_conns(calib);
  val_dac->update(codes_dac);
  return prof;
}
