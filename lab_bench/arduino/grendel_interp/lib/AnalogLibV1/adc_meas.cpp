#include "AnalogLib.h"
#include "assert.h"
#include "fu.h"
#include "calib_util.h"
#include "emulator.h"


emulator::physical_model_t adc_draw_random_model(profile_spec_t spec){
  emulator::physical_model_t model; 
  emulator::ideal(model);
  Fabric::Chip::Tile::Slice::ChipAdc::computeInterval(spec.state.adc,
                                                      in0Id,
                                                      model.in0.min,
                                                      model.in0.max);
  emulator::bound(model.in1,-1,1);
  return model;
}

profile_t Fabric::Chip::Tile::Slice::ChipAdc::measure(profile_spec_t spec){
#ifdef EMULATE_HARDWARE
  float std;
  sprintf(FMTBUF,"measured value: in=(%f,%f)\n",  \
          spec.inputs[0], \
          spec.inputs[1]);
  print_info(FMTBUF);

  float * input = prof::get_input(spec,port_type_t::in0Id);
  float output = Fabric::Chip::Tile::Slice::ChipAdc::computeOutput(spec.state.adc,*input);

  emulator::physical_model_t model = adc_draw_random_model(spec);
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
profile_t Fabric::Chip::Tile::Slice::ChipAdc::measureConstVal(profile_spec_t spec){
  update(this->m_state);

  Fabric::Chip::Tile::Slice::Dac * val_dac = parentSlice->dac;
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
  mean = this->digitalCodeToValue(mean);
  profile_t prof = prof::make_profile(spec,
                                      mean,
                                      variance);

	conn0.brkConn();
	val_dac->setEnable(false);

  cutil::restore_conns(calib);
  val_dac->update(codes_dac);
  return prof;
}
