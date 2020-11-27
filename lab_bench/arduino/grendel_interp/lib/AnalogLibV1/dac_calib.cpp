#include "AnalogLib.h"
#include <float.h>
#include "assert.h"
#include "calib_util.h"
#include "slice.h"
#include "dac.h"
#include "Arduino.h"

#define CALIB_NPTS 7
const float TEST_POINTS[CALIB_NPTS] = {0,0.875,0.5,-0.875,-0.5,0.25,-0.25};
unsigned int N_DAC_POINTS_TESTED = 0;

//#define DEBUG_DAC_CAL
float Fabric::Chip::Tile::Slice::Dac::getLoss(calib_objective_t obj){
  float loss = 0;
  switch(obj){
  case CALIB_MINIMIZE_ERROR:
    loss = calibrateMinError();
    break;
  case CALIB_MAXIMIZE_DELTA_FIT:
    loss = calibrateMaxDeltaFit();
    break;
  case CALIB_FAST:
    loss = calibrateFast();
    break;
  default:
    error("unimplemented dac");
    break;
  }
  return loss;
}



void Fabric::Chip::Tile::Slice::Dac::calibrate (calib_objective_t obj)
{
  // backup state
  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  dac_state_t codes_dac = this->m_state;

  cutil::calibrate_t calib;
  cutil::initialize(calib);

  cutil::buffer_dac_conns(calib,this);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

  //setup
	Connection dac_to_tile = Connection ( out0, parentSlice->tileOuts[3].in0 );
	Connection tile_to_chip = Connection ( parentSlice->tileOuts[3].out0,
                                         parentSlice->parentTile->parentChip->tiles[3].slices[2].chipOutput->in0 );
  this->m_state.source = DSRC_MEM;
  dac_to_tile.setConn();
	tile_to_chip.setConn();

  N_DAC_POINTS_TESTED = 0;
  //populate calibration table
  cutil::calib_table_t calib_table = cutil::make_calib_table();
  for(int nmos=0; nmos < MAX_NMOS; nmos += 1){
    this->m_state.nmos = nmos;
    for(int gain_cal=0; gain_cal < MAX_GAIN_CAL; gain_cal += 4){
      this->m_state.gain_cal=gain_cal;
      //compute loss for combo
      float loss = getLoss(obj);
      cutil::update_calib_table(calib_table,loss,2,nmos,gain_cal);
      sprintf(FMTBUF,"dac-cal nmos=%d\tgain_cal=%d\tloss=%f\n",nmos,gain_cal,loss);
      print_info(FMTBUF);
    }
  }
  sprintf(FMTBUF,"BEST-nmos dac-cal nmos=%d\tloss=%f\n",
          calib_table.state[0],calib_table.loss);
  print_info(FMTBUF);

  this->m_state.nmos = calib_table.state[0];
  for(int gain_cal=0; gain_cal < MAX_GAIN_CAL; gain_cal += 1){
    this->m_state.gain_cal=gain_cal;
    //compute loss for combo
    float loss = getLoss(obj);
    cutil::update_calib_table(calib_table,loss,2,
                              this->m_state.nmos,
                              gain_cal);
    sprintf(FMTBUF,"dac-cal nmos=%d\tgain_cal=%d\tloss=%f",nmos,gain_cal,loss);
    print_info(FMTBUF);
  }

  int best_nmos = calib_table.state[0];
  int best_gain_cal = calib_table.state[1];
  print_info("======");
  sprintf(FMTBUF,"BEST dac-cal nmos=%d\tgain_cal=%d\tloss=%f",
          best_nmos,best_gain_cal,calib_table.loss);
  print_info(FMTBUF);
  sprintf(FMTBUF,"Tested Points: %d\n", N_DAC_POINTS_TESTED);
  print_info(FMTBUF);

  // teardown
  update(codes_dac);
  tile_to_chip.brkConn();
  dac_to_tile.brkConn();
  cutil::restore_conns(calib);
  //set hidden codes to best codes
  this->m_state = codes_dac;
  this->m_state.nmos = best_nmos;
  this->m_state.gain_cal = best_gain_cal;
  update(this->m_state);
}

float Fabric::Chip::Tile::Slice::Dac::calibrateMaxDeltaFit(){
  float expected[CALIB_NPTS];
  float errors[CALIB_NPTS];
  float max_std=0.0;
  for(int i=0; i < CALIB_NPTS; i += 1){
    float const_val = TEST_POINTS[i];
    this->setConstant(const_val);
    float target = Fabric::Chip::Tile::Slice::Dac::computeOutput(this->m_state);
    float mean,variance;
    mean = this->fastMeasureValue(variance);
#ifdef DEBUG_DAC_CAL
    sprintf(FMTBUF,"dac-cal-maxfit in_val=%f targ=%f meas=%f\n",
            const_val,target,mean);
    print_info(FMTBUF);
#endif
    N_DAC_POINTS_TESTED += 1;
    errors[i] = mean-target;
    expected[i] = target;
    max_std = max(sqrt(variance),max_std);
  }
  float gain_mean,bias,rsq,max_error,avg_error;
  util::linear_regression(expected,errors,CALIB_NPTS,
                          gain_mean,bias,rsq,max_error,avg_error);
  float min,max;
  this->computeInterval(this->m_state, out0Id, min, max);
  return cutil::compute_loss(bias,max_std,avg_error,
                             1.0+gain_mean,
                             max,
                             0.03,1.0);

}
float Fabric::Chip::Tile::Slice::Dac::calibrateMinError(){
  float loss_total = 0;
  for(int i=0; i < CALIB_NPTS; i += 1){
    float const_val = TEST_POINTS[i];
    this->setConstant(const_val);
    float target = Fabric::Chip::Tile::Slice::Dac::computeOutput(this->m_state);
    float mean,variance;
    N_DAC_POINTS_TESTED += 1;
    mean = this->fastMeasureValue(variance);
#ifdef DEBUG_DAC_CAL
    sprintf(FMTBUF,"dac-cal-min in_val=%f targ=%f meas=%f\n",
            const_val,target,mean);
    print_info(FMTBUF);
#endif
    loss_total += fabs(target-mean);
  }
  return loss_total/CALIB_NPTS;
}

float Fabric::Chip::Tile::Slice::Dac::calibrateFast(){
  float const_val = 1.0;
  this->setConstant(const_val);
  float target = Fabric::Chip::Tile::Slice::Dac::computeOutput(this->m_state);
  float mean,variance;
  mean = this->fastMeasureValue(variance);
#ifdef DEBUG_DAC_CAL
  sprintf(FMTBUF,"dac-cal-fast in_val=%f targ=%f meas=%f\n",
          const_val,target,mean);
  print_info(FMTBUF);
#endif
  return fabs(mean-target);
}
