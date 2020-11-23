#include "AnalogLib.h"
#include <float.h>
#include "assert.h"
#include "calib_util.h"
#include "slice.h"
#include "dac.h"
#include "emulator.h"

#define DEBUG_DAC_PROF

emulator::physical_model_t dac_draw_random_model(profile_spec_t spec){
  emulator::physical_model_t model;
  emulator::ideal(model);
  emulator::bound(model.in0,-1,1);
  emulator::bound(model.in1,-1,1);
  return model;
 

}

profile_t Fabric::Chip::Tile::Slice::Dac::measure(profile_spec_t spec){
#ifdef EMULATE_HARDWARE
  float std;
  float * input = prof::get_input(spec,port_type_t::in0Id);
  float output = Fabric::Chip::Tile::Slice::Dac::computeOutput(spec.state.dac);

  emulator::physical_model_t model = dac_draw_random_model(spec);
  float result = emulator::draw(model,0.0,0.0,output,std);
  sprintf(FMTBUF,"output=%f result=%f\n", output,result);
  print_info(FMTBUF);
  profile_t prof = prof::make_profile(spec, result,
                                      std);
  return prof;

#else
  return this->measureConstVal(spec);
#endif
}

profile_t Fabric::Chip::Tile::Slice::Dac::measureConstVal(profile_spec_t spec)
{
  if(!this->m_state.enable){
    profile_t dummy;
    print_log("DAC not enabled");
    return dummy;
  }
  float scf = util::range_to_coeff(this->m_state.range);
  cutil::calibrate_t calib;
  cutil::initialize(calib);

  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  dac_state_t codes_dac = this->m_state;
  this->m_state = spec.state.dac;
  if(spec.state.dac.source == DSRC_LUT0 ||
     spec.state.dac.source == DSRC_LUT1 ||
     spec.state.dac.source == DSRC_EXTERN){
    this->setConstant(spec.inputs[in0Id]);
    this->m_state.source = DSRC_MEM;
  }
  //setConstant(in);
  update(this->m_state);

  cutil::buffer_dac_conns(calib,this);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile
                              ->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

	Connection dac_to_tile = Connection ( out0, parentSlice->tileOuts[3].in0 );
	Connection tile_to_chip = Connection ( parentSlice->tileOuts[3].out0,
                                         parentSlice->parentTile
                                         ->parentChip->tiles[3].slices[2].chipOutput->in0 );

  dac_to_tile.setConn();
	tile_to_chip.setConn();
  this->m_state = spec.state.dac;
  float target = this->computeOutput(this->m_state);
  float mean,variance;
  mean = this->fastMeasureValue(variance);
#ifdef DEBUG_DAC_PROF
  sprintf(FMTBUF,"prof-dac code=%d targ=%f mean=%f variance=%f\n",
          this->m_state.const_code, target,mean,variance);
  print_info(FMTBUF);
#endif
  const int mode = 0;
  const float in1 = 0.0;
  profile_t result = prof::make_profile(spec,
                                        mean,
                                        sqrt(variance));
  if(!calib.success){
    result.status = profile_status_t::FAILED_TO_CALIBRATE;
  }
	tile_to_chip.brkConn();
  dac_to_tile.brkConn();

  cutil::restore_conns(calib);
  update(codes_dac);
  return result;
}


