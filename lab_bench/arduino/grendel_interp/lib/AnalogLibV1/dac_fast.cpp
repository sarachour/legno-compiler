#include "AnalogLib.h"
#include <float.h>
#include "assert.h"
#include "calib_util.h"
#include "slice.h"
#include "dac.h"

// this model for the high-mode dac.

void fast_calibrate_dac(Fabric::Chip::Tile::Slice::Dac * aux_dac){
  if(!aux_dac->calibrated){
    // do a naive calibration to make sure we have enough range.
    dac_code_t codes = aux_dac->m_codes;
    aux_dac->setEnable(true);
    aux_dac->setRange(RANGE_MED);
    aux_dac->setInv(false);
    // basically a heuristic that maximizes dynamic range of dac.
    aux_dac->calibrate(CALIB_FAST);
    //aux_dac->m_codes.nmos = 7;
    //aux_dac->m_codes.gain_cal = 63;
    aux_dac->calibrated = true;
    aux_dac->calib_codes = aux_dac->m_codes;
    aux_dac->fastMakeDacModel();
    aux_dac->m_codes = codes;

  }
  aux_dac->m_codes.pmos = aux_dac->calib_codes.pmos;
  aux_dac->m_codes.nmos = aux_dac->calib_codes.nmos;
  aux_dac->m_codes.gain_cal = aux_dac->calib_codes.gain_cal;
  aux_dac->update(aux_dac->m_codes);
}
void Fabric::Chip::Tile::Slice::Dac::fastMakeDacModel(){
#define NPTS 5
  float values[NPTS] = {-10,-5,0,5,10};
  float measurements[NPTS];
  float codes[NPTS];
  for(int i=0; i < NPTS; i += 1){
    measurements[i] = this->fastMakeHighValue(values[i],0.2);
    codes[i] = this->m_codes.const_code;
    sprintf(FMTBUF," v=%f m=%f c=%f", values[i],measurements[i],codes[i]);
    print_info(FMTBUF);
  }
  float max_error,avg_error;
  util::linear_regression(codes,measurements,NPTS,
                          this->dac_model.alpha,
                          this->dac_model.beta,
                          this->dac_model.rsq,
                          max_error,avg_error);
  sprintf(FMTBUF,"alpha=%f beta=%f rsq=%f", dac_model.alpha,
          dac_model.beta,
          dac_model.rsq);
  print_info(FMTBUF);
}
float Fabric::Chip::Tile::Slice::Dac::fastMakeValue(float target){
  if(fabs(target) < 0.9){
    return fastMakeMedValue(target, 0.02);
  }
  else{
    return fastMakeHighValue(target,0.2);
  }
}
float Fabric::Chip::Tile::Slice::Dac::fastMakeMedValue(float target,
                                                       float max_error){

  dac_code_t codes_dac = m_codes;
  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_dac_conns(calib,this);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice
                              ->parentTile->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

	Connection this_dac_to_tile = Connection ( out0, parentSlice->tileOuts[3].in0 );
	Connection tile_to_chip = Connection ( parentSlice->tileOuts[3].out0,
                                         parentSlice->parentTile
                                         ->parentChip->tiles[3].slices[2].chipOutput->in0 );
  this->setEnable(true);
  this->setRange(RANGE_MED);
  this->setInv(false);
  this->setSource(DSRC_MEM);

  fast_calibrate_dac(this);

  this_dac_to_tile.setConn();
  tile_to_chip.setConn();

  // start at what the value would be if the gain was one.
  this->setConstant(target);
  // start out with no code offset
  int delta = 0;
  // store the base code
  int base_code = this->m_codes.const_code;
  // start off with a terrible measured difference
  float mean = 1e6;
  // adjust the code until we fall within some bound of our
  // target difference
  while(fabs(mean - target) > max_error){
    int next_code = base_code + delta;
    if(next_code < 0 || next_code > 255){
      break;
    }
    this->m_codes.const_code = next_code;
    update(this->m_codes);
    mean = util::meas_chip_out(this);
    /*
    sprintf(FMTBUF,"DIFF delta=%d targ=%f meas=%f err=%f max_err=%f suc=%s",
            next_code,target,mean,fabs(mean-target),max_error,
            fabs(mean-target) > max_error ? "n" : "y");
    print_info(FMTBUF);
    */
    delta += target < mean ? -1 : +1;
  }
  this_dac_to_tile.brkConn();
  tile_to_chip.brkConn();
  cutil::restore_conns(calib);
  return mean;


}
// this method makes an approximate current value.
float Fabric::Chip::Tile::Slice::Dac::fastMakeHighValue(float target,
                                                        float max_error){
  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice].dac;
  dac_code_t codes_dac = m_codes;
  dac_code_t codes_ref = ref_dac->m_codes;
  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_dac_conns(calib,this);
  cutil::buffer_dac_conns(calib,ref_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice
                              ->parentTile->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

	Connection this_dac_to_tile = Connection ( out0, parentSlice->tileOuts[3].in0 );
	Connection ref_dac_to_tile = Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0 );
  // conn3
	Connection tile_to_chip = Connection ( parentSlice->tileOuts[3].out0,
                                         parentSlice->parentTile->parentChip->tiles[3].slices[2].chipOutput->in0 );


  ref_dac->setEnable(true);
  ref_dac->setRange(RANGE_HIGH);
  ref_dac->setInv(false);
  ref_dac->setSource(DSRC_MEM);
  fast_calibrate_dac(ref_dac);

  this->setEnable(true);
  this->setRange(RANGE_HIGH);
  this->setInv(false);
  this->setSource(DSRC_MEM);
  fast_calibrate_dac(this);

  this_dac_to_tile.setConn();
  ref_dac_to_tile.setConn();
  tile_to_chip.setConn();

  // make sure the reference values are always
  // the opposite sign of the target signal.
  float value = target < 0 ? -1e-6 : 1e-6;
  float step = 0.5;

  // determine zero for the reference dac
  this_dac_to_tile.brkConn();
  ref_dac_to_tile.setConn();
  ref_dac->setConstant(0.0);
  float ref_value = util::meas_chip_out(this);

  // determine zero for this dac
  ref_dac_to_tile.brkConn();
  this_dac_to_tile.setConn();
  this->setConstant(0.0);
  float dac_value = util::meas_chip_out(this);

  // add these dacs togeth
  this_dac_to_tile.setConn();
  ref_dac_to_tile.setConn();
  bool update_ref = true;
  // connect reference dac.
  // telescope the dacs outward until we find
  // a value for the reference dac that is within
  // one step of the target
  while(fabs(ref_value) < fabs(target)
        && fabs(value) <= 10.0){
    float old_value = value;
    // telescope outward
    value = -(value < 0 ? value - step : value + step);
    float mean = -99.0;
    if(update_ref){
      ref_dac->setConstant((value)*0.1);
      mean = util::meas_chip_out(this);
      ref_value = -dac_value + mean;
    }
    else{
      this->setConstant((value)*0.1);
      mean = util::meas_chip_out(this);
      dac_value = -ref_value + mean;
    }
    // emit information
    update_ref = !update_ref;
  }
  // compute the expected difference, with respect to this
  // reference dac
  float target_diff = target + ref_value;
  // start at what the value would be if the gain was one.
  this->setConstant(target*0.1);
  // start out with no code offset
  int delta = 0;
  // store the base code
  int base_code = this->m_codes.const_code;
  // start off with a terrible measured difference
  float mean = 1e6;
  // adjust the code until we fall within some bound of our
  // target difference
  while(fabs(mean - target_diff) > max_error){
    int next_code = base_code + delta;
    if(next_code < 0 || next_code > 255){
      break;
    }
    this->m_codes.const_code = next_code;
    update(this->m_codes);
    mean = util::meas_fast_chip_out(this);
    /*
    sprintf(FMTBUF,"DIFF delta=%d targ=%f meas=%f err=%f max_err=%f suc=%s",
            next_code,target_diff,mean,fabs(mean-target_diff),max_error,
            fabs(mean-target_diff) > max_error ? "n" : "y");
    print_debug(FMTBUF);
    */
    delta += target_diff < mean ? -1 : +1;
  }

  this_dac_to_tile.brkConn();
  ref_dac_to_tile.brkConn();
  tile_to_chip.brkConn();
  cutil::restore_conns(calib);
  ref_dac->update(codes_ref);

  return mean - ref_value;
}

float Fabric::Chip::Tile::Slice::Dac::fastMeasureValue(float& variance){
  if(this->m_codes.range == RANGE_HIGH){
    return fastMeasureHighValue(variance);
  }
  else {
    return fastMeasureMedValue(variance);
  }
}

float Fabric::Chip::Tile::Slice::Dac::fastMeasureMedValue(float& variance){
  dac_code_t codes_dac = m_codes;
  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_dac_conns(calib,this);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice
                              ->parentTile->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);
	Connection this_dac_to_tile = Connection ( out0, parentSlice->tileOuts[3].in0 );
	Connection tile_to_chip = Connection ( parentSlice->tileOuts[3].out0,
                                         parentSlice->parentTile->parentChip->tiles[3].slices[2].chipOutput->in0 );


  this_dac_to_tile.setConn();
  tile_to_chip.setConn();
  // measure mean and variance of signal
  float mean;
  util::meas_dist_chip_out(this,mean,variance);

  this_dac_to_tile.brkConn();
  tile_to_chip.brkConn();
  cutil::restore_conns(calib);
  update(codes_dac);
  return mean;


}

/*
utility function for fastMeasureHighValue

futz with the value of the dac until the measured signal
is within range.

*/
bool update_code(int& code,int step){
  int next_code = code + step;
  bool terminate_search = false;
  if(next_code < 0 || next_code > 255){
    next_code = min(255,max(0,next_code));
  }
  if(next_code + step < 0 || next_code + step > 255){
    terminate_search = true;
  }
  if(code >= 128 && next_code < 128){
    next_code = 128;
    terminate_search = true;
  }
  if(code <= 128 && next_code > 128){
    next_code = 128;
    terminate_search = true;
  }
  code = next_code;
  return terminate_search;
}
float tune_dac_value(Fabric::Chip::Tile::Slice::Dac* dac,
                     float init_value,
                     float max_meas,
                     float& meas){
  float step = init_value < 0 ? 3 : -3;
  bool terminate_search;
  meas = util::meas_fast_chip_out(dac);
  do {
    int code = dac->m_codes.const_code;
    terminate_search = update_code(code,step);
    dac->setConstantCode(code);
    meas = util::meas_fast_chip_out(dac);
  } while(fabs(meas) < max_meas && !terminate_search);

  return Fabric::Chip::Tile::Slice::Dac::computeOutput(dac->m_codes);
}
float find_ref_dac_code(Fabric::Chip::Tile::Slice::Dac* dac,
                        int code, float max_meas){

  dac->setConstantCode(code);
  float meas = util::meas_fast_chip_out(dac);
  const int step = 3;
  bool terminate_search = false;
  while(fabs(meas) > max_meas){
    code += meas < 0 ? step : -step;
    if(code < 0 || code > 255){
      error("find_ref: code out of bounds");
    }
    dac->setConstantCode(code);
    meas = util::meas_fast_chip_out(dac);
  }
  return meas;
}

// very quickly measures a value using uncalibrated dacs.
float Fabric::Chip::Tile::Slice::Dac::fastMeasureHighValue(float& variance){

  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice].dac;
  dac_code_t codes_dac = m_codes;
  dac_code_t codes_ref = ref_dac->m_codes;
  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_dac_conns(calib,this);
  cutil::buffer_dac_conns(calib,ref_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice
                              ->parentTile->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

	Connection this_dac_to_tile = Connection ( out0, parentSlice->tileOuts[3].in0 );
	Connection ref_dac_to_tile = Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0 );
  // conn3
	Connection tile_to_chip = Connection ( parentSlice->tileOuts[3].out0,
                                         parentSlice->parentTile->parentChip->tiles[3].slices[2].chipOutput->in0 );


  this->setEnable(true);
  this->setRange(RANGE_HIGH);
  this->setSource(DSRC_MEM);

  ref_dac->setEnable(true);
  ref_dac->setRange(RANGE_HIGH);
  ref_dac->setSource(DSRC_MEM);
  //calibrate reference
  fast_calibrate_dac(ref_dac);

  this_dac_to_tile.setConn();
  ref_dac_to_tile.setConn();
  tile_to_chip.setConn();

  const float max_meas_val = 0.8;
  const float max_ref_dist = 0.8;
  //compute the floating point value from the dac code.
  int distance = fabs(this->m_codes.const_code-128);
  if(this->m_codes.const_code < 128)
    ref_dac->m_codes.const_code = min(128 + distance,255);
  else
    ref_dac->m_codes.const_code = max(128 - distance,0);

  float meas = find_ref_dac_code(ref_dac,
                                 ref_dac->m_codes.const_code,
                                 max_ref_dist);

  dac_model_t model = ref_dac->dac_model;
  float ref = ref_dac->m_codes.const_code*model.alpha + model.beta;
  float out = meas - ref;
  //sprintf(FMTBUF,"ref=%f meas=%f out=%f", ref,meas,out);
  //print_info(FMTBUF);
  ref_dac_to_tile.brkConn();
  this_dac_to_tile.brkConn();
  tile_to_chip.brkConn();
  cutil::restore_conns(calib);
  update(codes_dac);
  ref_dac->update(codes_ref);
  return out;
}
