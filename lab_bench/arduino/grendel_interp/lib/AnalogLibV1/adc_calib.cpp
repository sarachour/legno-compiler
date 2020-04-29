#include "AnalogLib.h"
#include "assert.h"
#include "fu.h"
#include "calib_util.h"
#include "profile.h"


bool helper_check_steady(Fabric * fab,
                         Fabric::Chip::Tile::Slice::ChipAdc* adc,
                         Fabric::Chip::Tile::Slice::Dac* dac,
                         float value
                         ){
  dac_state_t codes_dac = dac->m_state;
  dac->setConstant(value);
  dac->update(dac->m_state);
  bool success=true;
  // get the adc code at that value
	unsigned char adcPrev = adc->getData();
	for (unsigned char rep=0; success&&(rep<16); rep++){
    // determine if adc code is the same value as the previous value.
		success &= adcPrev==adc->getData();
  }
  dac->update(codes_dac);
	return success;
}


bool Fabric::Chip::Tile::Slice::ChipAdc::testValidity(Fabric::Chip::Tile::Slice::Dac * val_dac){
  Fabric* fab = parentSlice->parentTile->parentChip->parentFabric;
  const float VALID_TEST_POINTS[3] = {0,1,-1};
  bool succ = true;
  for(int i = 0; i < 3; i += 1){
    succ &= helper_check_steady(fab,
                             this,
                             val_dac,
                             VALID_TEST_POINTS[i]);
    if(!succ){
      return false;
    }
  }
  return true;
}


#define CALIB_NPTS 5
const float TEST_POINTS[CALIB_NPTS] = {0,0.5,-0.5,0.875,-0.875};

float Fabric::Chip::Tile::Slice::ChipAdc::calibrateFast(Fabric::Chip::Tile::Slice::Dac * val_dac){

  float mean,variance;
  float in_val = val_dac->fastMakeValue(0.0);
  float target =Fabric::Chip::Tile::Slice::ChipAdc::computeOutput(this->m_state,
                                                                  in_val);

  util::meas_dist_adc(this,mean,variance);
  return fabs(target-mean);
}

float Fabric::Chip::Tile::Slice::ChipAdc::calibrateMinError(Fabric::Chip::Tile::Slice::Dac * val_dac){

  float mean,variance;
  float loss_total=0.0;
  for(int i=0; i < CALIB_NPTS; i += 1){
    float test_pt = TEST_POINTS[i]*util::range_to_coeff(this->m_state.range);
    float in_val = val_dac->fastMakeValue(test_pt);
    float target =Fabric::Chip::Tile::Slice::ChipAdc::computeOutput(this->m_state,
                                                                   in_val);

    util::meas_dist_adc(this,mean,variance);
    loss_total += fabs(target-mean);
  }
  return loss_total/CALIB_NPTS;
}
float Fabric::Chip::Tile::Slice::ChipAdc::calibrateMaxDeltaFit(Fabric::Chip::Tile::Slice::Dac * val_dac){
  float mean,variance;
  float highest_std = 0.0;
  float errors[CALIB_NPTS];
  float expected[CALIB_NPTS];
  for(int i=0; i < CALIB_NPTS; i += 1){
    // FIXME: this is definitely wrong. Why is TEST_POINTS being used over target.
    float test_pt = TEST_POINTS[i]*util::range_to_coeff(this->m_state.range);
    float in_val = val_dac->fastMakeValue(test_pt);
    float target =Fabric::Chip::Tile::Slice::ChipAdc::computeOutput(this->m_state,
                                                                    in_val);

    util::meas_dist_adc(this,mean,variance);
    expected[i] = TEST_POINTS[i];
    errors[i] = ((mean-128.0)/128.0)-expected[i];
    highest_std = max(sqrt(variance)/128.0,highest_std);
  }
  float gain_mean,bias,rsq,avg_error,max_error;
  util::linear_regression(expected,errors,CALIB_NPTS,
                          gain_mean,bias,rsq,max_error,avg_error);
  // put no emphasis on deviation because parameter setting doesn't
  // change it that much.
  return cutil::compute_loss(bias,highest_std,avg_error,
                             1.0+gain_mean,     \
                             RANGE_MED, 0.0, 1.0);
}

float Fabric::Chip::Tile::Slice::ChipAdc::getLoss(calib_objective_t obj,
                                                  Dac * val_dac){
  float loss=0.0;
  switch(obj){
  case CALIB_MINIMIZE_ERROR:
    loss = calibrateMinError(val_dac);
    break;
  case CALIB_MAXIMIZE_DELTA_FIT:
    loss = calibrateMaxDeltaFit(val_dac);
    break;
  case CALIB_FAST:
    loss = calibrateFast(val_dac);
    break;
  default:
    error("unimplemented adc");
    break;
  }
  return loss;
}
void Fabric::Chip::Tile::Slice::ChipAdc::calibrate (calib_objective_t obj) {

  Fabric::Chip::Tile::Slice::Dac * val_dac = parentSlice->dac;
  //backup
  adc_state_t codes_adc = this->m_state;
  dac_state_t codes_dac = val_dac->m_state;
  const float EPS = 1e-4;

  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_dac_conns(calib,val_dac);
  cutil::buffer_adc_conns(calib,this);
  cutil::break_conns(calib);

  val_dac->setEnable(true);
	Connection conn0 = Connection ( val_dac->out0, in0 );
	conn0.setConn();

  print_info("calibrating adc...");
  cutil::calib_table_t calib_table = cutil::make_calib_table();
  unsigned char opts[] = {nA100,nA200,nA300,nA400};
  int signs[] = {-1,1};
  bool found_code = false;
  for(unsigned char fs=0; fs < 4 && !found_code; fs += 1){
    this->m_state.lower_fs = opts[fs];
    this->m_state.upper_fs = opts[fs];

    for(unsigned char spread=0; spread < 32 && !found_code; spread+=1){
      sprintf(FMTBUF,"fs=%d spread=%d",
              fs, spread);
      print_info(FMTBUF);
      for(unsigned char lsign=0; lsign < 2 && !found_code; lsign +=1){
        for(unsigned char usign=0; usign < 2 && !found_code; usign +=1){
          this->m_state.lower = 31+spread*signs[lsign];
          this->m_state.upper = 31+spread*signs[usign];
          this->m_state.nmos = 0;
          update(this->m_state);
          if(!testValidity(val_dac)){
            continue;
          }

          for(int nmos=0; nmos < MAX_NMOS && !found_code; nmos += 1){
            float error;
            this->m_state.nmos = nmos;
            update(this->m_state);
            val_dac->setConstant(0.0);
            binsearch::find_bias(this,
                                 128.0,
                                 this->m_state.i2v_cal,
                                 error,
                                 MEAS_ADC);
            sprintf(FMTBUF,"fs=(%d,%d) def=(%d,%d) nmos=%d i2v=%d loss=%f",
                    this->m_state.lower_fs,
                    this->m_state.upper_fs,
                    this->m_state.lower,
                    this->m_state.upper,
                    nmos,
                    this->m_state.i2v_cal,
                    error);
            print_info(FMTBUF);
            if(error > 0.5){
              continue;
            }
            update(this->m_state);
            float loss = getLoss(obj,val_dac);
            sprintf(FMTBUF,"fs=(%d,%d) def=(%d,%d) nmos=%d i2v=%d loss=%f",
                    this->m_state.lower_fs,
                    this->m_state.upper_fs,
                    this->m_state.lower,
                    this->m_state.upper,
                    nmos,
                    this->m_state.i2v_cal,
                    loss);
            print_info(FMTBUF);
            cutil::update_calib_table(calib_table,loss,6,
                                      this->m_state.lower_fs,
                                      this->m_state.upper_fs,
                                      this->m_state.lower,
                                      this->m_state.upper,
                                      nmos,
                                      this->m_state.i2v_cal);
            found_code = true;
            break;
            //if(fabs(calib_table.loss) < EPS && calib_table.set)
            // break;
          }
        }
      }
    }
  }
  if(!calib_table.set){
    error("could not calibrate adc..");
  }
  conn0.brkConn();
  val_dac->update(codes_dac);
  this->update(codes_adc);

  this->m_state.lower_fs = calib_table.state[0];
  this->m_state.upper_fs = calib_table.state[1];
  this->m_state.lower = calib_table.state[2];
  this->m_state.upper = calib_table.state[3];
  this->m_state.nmos = calib_table.state[4];
  this->m_state.i2v_cal = calib_table.state[5];
  update(this->m_state);

  sprintf(FMTBUF,"BEST fs=(%d,%d) def=(%d,%d) nmos=%d i2v=%d loss=%f",
          this->m_state.lower_fs,
          this->m_state.upper_fs,
          this->m_state.lower,
          this->m_state.upper,
          this->m_state.nmos,
          this->m_state.i2v_cal,
          calib_table.loss);
  print_info(FMTBUF);
}
