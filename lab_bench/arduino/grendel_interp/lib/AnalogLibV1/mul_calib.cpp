#include "AnalogLib.h"
#include "fu.h"
#include "mul.h"
#include "calib_util.h"
#include <float.h>

#define MULT_CALIB_NPTS 3
#define MULT_TOTAL_NPTS (1 + MULT_CALIB_NPTS*MULT_CALIB_NPTS)

#define VGA_CALIB_NPTS 5
#define VGA_TOTAL_NPTS (1 + VGA_CALIB_NPTS*VGA_CALIB_NPTS)

const float TEST0_MULT_POINTS[MULT_CALIB_NPTS] = {0.75,-0.5,0.5};
const float TEST1_MULT_POINTS[MULT_CALIB_NPTS] = {-0.5,0.5,0.0};

const float TEST0_VGA_POINTS[VGA_CALIB_NPTS] = {-0.75,0.75,-0.5,0.5,0.0};
const float TEST1_VGA_POINTS[VGA_CALIB_NPTS] = {-0.75,0.75,-0.5,0.5,0.0};

#define DEBUG_MULT_CAL

unsigned int N_MULT_POINTS_TESTED = 0;
float Fabric::Chip::Tile::Slice::Multiplier::getLoss(calib_objective_t obj,
                                                     Dac * val0_dac,
                                                     Dac * val1_dac,
                                                     Dac * ref_dac,
                                                     bool ignore_bias){
  float loss = 999.0;
  switch(obj){
  case CALIB_MINIMIZE_ERROR:
    loss = calibrateMinError(val0_dac,val1_dac,ref_dac);
    break;
  case CALIB_MAXIMIZE_DELTA_FIT:
    loss = calibrateMaxDeltaFit(val0_dac,val1_dac,ref_dac,ignore_bias);
    break;
  default:
    error("mult calib : unimplemented");
  }
  return loss;
}
float Fabric::Chip::Tile::Slice::Multiplier::calibrateMaxDeltaFit(Dac * val0_dac,
                                                                  Dac * val1_dac,
                                                                  Dac * ref_dac,
                                                                  bool ignore_bias){
  if(this->m_state.vga){
    return calibrateMaxDeltaFitVga(val0_dac, ref_dac,ignore_bias);
  }
  else{
    return calibrateMaxDeltaFitMult(val0_dac, val1_dac, ref_dac,ignore_bias);
  }
}


float Fabric::Chip::Tile::Slice::Multiplier::calibrateMinError(Dac * val0_dac,
                                                               Dac * val1_dac,
                                                               Dac * ref_dac){
  if(this->m_state.vga){
    return calibrateMinErrorVga(val0_dac, ref_dac);
  }
  else{
    return calibrateMinErrorMult(val0_dac, val1_dac, ref_dac);
  }
}

float Fabric::Chip::Tile::Slice::Multiplier::calibrateHelperVga(Dac * val_dac,
                                                                Dac * ref_dac,
                                                                float* observations,
                                                                float* expected,
                                                                int& npts){
  const bool meas_steady = false;
  float variance,mean;
  float max_std = 0.0;

  npts = 0;
  Fabric::Chip::Connection ref_to_tileout =
    Fabric::Chip::Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0);
  Connection dac0_to_in0 = Connection (val_dac->out0, this->in0);

  ref_to_tileout.setConn();
  dac0_to_in0.setConn();
  for(int i=0; i < VGA_CALIB_NPTS; i += 1){
    for(int j=0; j < VGA_CALIB_NPTS; j += 1){
      float in0 = TEST0_VGA_POINTS[i];
      float in1 = TEST1_VGA_POINTS[j];
      val_dac->setConstant(in0);
      this->setGain(in1);
      this->update(this->m_state);
      float target_in0 = val_dac->fastMeasureValue(variance);
      float target_out = this->computeOutput(this->m_state,
                                             target_in0,
                                             0.0);

      bool succ = cutil::measure_signal_robust(this,
                                            ref_dac,
                                            target_out,
                                            meas_steady,
                                            mean,
                                            variance);
#ifdef DEBUG_MULT_CAL
      sprintf(FMTBUF,"vga-h dac=(%f,%f) in0=%f coeff=%f targ=%f mean=%f\n",
              in0,in1,target_in0, in1, target_out, mean);
      print_info(FMTBUF);
#endif
      N_MULT_POINTS_TESTED += 1;
      if(succ){
        observations[npts] = mean;
        expected[npts] = target_out;
        max_std = max(max_std,sqrt(variance));
        npts += 1;
      }
    }
  }
  return max_std;
}

float Fabric::Chip::Tile::Slice::Multiplier::calibrateHelperMult(Dac * val0_dac,
                                                                Dac * val1_dac,
                                                                Dac * ref_dac,
                                                                float* observations,
                                                                float* expected,
                                                                int& npts){
  const bool meas_steady = false;
  float dummy,mean;

  Connection ref_to_tileout =
    Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0);
  Connection dac0_to_in0 = Connection (val0_dac->out0, this->in0);
  Connection dac1_to_in1 = Connection (val1_dac->out0, this->in1);

  float max_std = 0.0;
  ref_to_tileout.setConn();
  dac0_to_in0.setConn();
  dac1_to_in1.setConn();

  npts = 0;
  for(int i=0; i < MULT_CALIB_NPTS; i += 1){
    for(int j=0; j < MULT_CALIB_NPTS; j += 1){
      float in0 = TEST0_MULT_POINTS[i];
      float in1 = TEST1_MULT_POINTS[j];
      float variance,mean;
      val0_dac->setConstant(in0);
      float target_in0 = val0_dac->fastMeasureValue(dummy);
      val1_dac->setConstant(in1);
      float target_in1 = val1_dac->fastMeasureValue(dummy);
      float target_out = this->computeOutput(this->m_state,
                                             target_in0,
                                             target_in1
                                             );

      bool succ = cutil::measure_signal_robust(this,
                                               ref_dac,
                                               target_out,
                                               meas_steady,
                                               mean,
                                               variance);
#ifdef DEBUG_MULT_CAL
      sprintf(FMTBUF,"mul-h dac=(%f,%f) in0=%f in1=%f targ=%f mean=%f\n",
              in0,in1,target_in0, target_in1, target_out, mean);
      print_info(FMTBUF);
#endif

      N_MULT_POINTS_TESTED += 1;
      if(succ){
        observations[npts] = mean;
        expected[npts] = target_out;
        max_std = max(max_std,sqrt(variance));
        npts += 1;
      }
    }
  }
  return max_std;
}
float Fabric::Chip::Tile::Slice::Multiplier::calibrateMaxDeltaFitMult(Dac * val0_dac,
                                                                      Dac * val1_dac,
                                                                      Dac * ref_dac,
                                                                      bool ignore_bias){
  int npts;
  float observed[MULT_TOTAL_NPTS];
  float expected[MULT_TOTAL_NPTS];
  float errors[MULT_TOTAL_NPTS];
  float max_std = this->calibrateHelperMult(val0_dac,
                            val1_dac,
                            ref_dac,
                            observed,
                            expected,
                            npts);
  for(int i=0; i < npts; i += 1){
    errors[i] = observed[i]-expected[i];
  }
  float gain_mean,rsq,bias,max_error,avg_error;
  util::linear_regression(expected,observed,npts,
                          gain_mean,bias,rsq,max_error,avg_error);
  float min,max;
  this->computeInterval(this->m_state, out0Id, min, max);
  // put no emphasis on deviation, because it will not adhere to 1.0
  return cutil::compute_loss(ignore_bias ? 0.0 : bias,
                             max_std,
                             avg_error,
                             gain_mean,
                             max,
                             0.0, 10.0);
}
float Fabric::Chip::Tile::Slice::Multiplier::calibrateMaxDeltaFitVga(Dac * val_dac,
                                                                     Dac * ref_dac,
                                                                     bool ignore_bias){
  int npts;
  float observed[VGA_TOTAL_NPTS];
  float expected[VGA_TOTAL_NPTS];
  float errors[VGA_TOTAL_NPTS];
  float highest_std = this->calibrateHelperVga(val_dac,ref_dac,
                                                observed,
                                                expected,
                                                npts);
  for(int i=0; i < npts; i += 1){
    errors[i] = observed[i]-expected[i];
  }
  float gain_mean,rsq,bias,max_error,avg_error;
  util::linear_regression(expected,errors,npts,
                          gain_mean,bias,rsq,max_error,avg_error);

  // put some emphasis on deviation because it is changed.
  // 0.015 before
  float min,max;
  this->computeInterval(this->m_state, out0Id, min, max);
  return cutil::compute_loss(ignore_bias ? 0.0 : bias,highest_std,
                             avg_error,
                             1.0+gain_mean,
                             max,
                             0.003,
                             10.0);
}
float Fabric::Chip::Tile::Slice::Multiplier::calibrateMinErrorVga(Dac * val_dac,
                                                                  Dac * ref_dac){
  int npts;
  float observed[VGA_TOTAL_NPTS];
  float expected[VGA_TOTAL_NPTS];
  this->calibrateHelperVga(val_dac,ref_dac,
                           observed,
                           expected,
                           npts);
  float total_loss = 0.0;
  for(int i=0; i < npts; i += 1){
    total_loss += fabs(observed[i]-expected[i]);
  }
  return total_loss/npts;
}
float Fabric::Chip::Tile::Slice::Multiplier::calibrateMinErrorMult(Dac * val0_dac,
                                                                   Dac * val1_dac,
                                                                   Dac * ref_dac){
  int npts;
  float observed[MULT_TOTAL_NPTS];
  float expected[MULT_TOTAL_NPTS];
  this->calibrateHelperMult(val0_dac,
                            val1_dac,
                            ref_dac,
                            observed,
                            expected,
                            npts);
  float total_loss = 0.0;
  for(int i=0; i < npts; i += 1){
    total_loss += fabs(observed[i]-expected[i]);
  }
  return total_loss/npts;
}

void Fabric::Chip::Tile::Slice::Multiplier::calibrateHelperFindMultBiasCodes(cutil::calib_table_t & table_bias, int stride,
                                                                         Dac* val0_dac,
                                                                         Dac* val1_dac,
                                                                         Dac* ref_dac,
                                                                         int bounds[6],
                                                                         float pos,
                                                                         float target_pos,
                                                                         float neg,
                                                                         float target_neg){

  Fabric::Chip::Connection ref_to_tileout =
    Fabric::Chip::Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0);
  ref_to_tileout.brkConn();

  cutil::calib_table_t in0_table = cutil::make_calib_table();
  this->m_state.port_cal[in0Id] = 32;
  this->m_state.port_cal[in1Id] = 32;
  this->m_state.port_cal[out0Id] = 32;
  for(int i=0; i < MAX_BIAS_CAL; i += 1){
    float error = 0.0;
    float meas1, meas2;
    this->m_state.port_cal[in0Id] = i;
    this->update(this->m_state);

    val0_dac->setConstant(0);

    val1_dac->setConstant(pos);
    meas1 = util::meas_fast_chip_out(this);
    error = max(fabs(meas1 - target_pos), error);

    val1_dac->setConstant(neg);
    meas2 = util::meas_fast_chip_out(this);
    error = max(fabs(meas2 - target_neg), error);
    N_MULT_POINTS_TESTED += 2;
#ifdef DEBUG_MULT_CAL
    sprintf(FMTBUF,"zero-in0 code=%d error=%f targ=(%f,%f) meas=(%f,%f)\n", i, error,
            target_neg,target_pos,meas1,meas2);
    print_info(FMTBUF);
#endif
    cutil::update_calib_table(in0_table,error,1,i);
  }
  this->m_state.port_cal[in0Id] = in0_table.state[0];

  sprintf(FMTBUF,"BEST-zero-in0 code=%d error=%f\n", in0_table.state[0], in0_table.loss);
  print_info(FMTBUF);


  cutil::calib_table_t in1_table = cutil::make_calib_table();
  for(int i=0; i < MAX_BIAS_CAL; i += 1){
    float error = 0.0;
    float meas1,meas2;

    this->m_state.port_cal[in1Id] = i;
    this->update(this->m_state);

    val0_dac->setConstant(0);

    val1_dac->setConstant(pos);
    meas1 = util::meas_fast_chip_out(this);
    error = max(fabs(meas1 - target_pos), error);

    val1_dac->setConstant(neg);
    meas2 = util::meas_fast_chip_out(this);
    error = max(fabs(meas2 - target_neg), error);
    cutil::update_calib_table(in1_table,error,1,i);
    N_MULT_POINTS_TESTED += 2;
#ifdef DEBUG_MULT_CAL
    sprintf(FMTBUF,"zero-in0 code=%d error=%f targ=(%f,%f) meas=(%f,%f)\n", i, error,
            target_neg,target_pos,meas1,meas2);
    print_info(FMTBUF);
#endif
  }
  this->m_state.port_cal[in1Id] = in1_table.state[0];

  sprintf(FMTBUF,"BEST-zero-out code=%d error=%f\n", in1_table.state[0], in1_table.loss);
  print_info(FMTBUF);


  cutil::calib_table_t out_table = cutil::make_calib_table();
  for(int i=0; i < MAX_BIAS_CAL; i += 1){
    float error = 0.0;
    float meas1,meas2;

    this->m_state.port_cal[out0Id] = i;
    this->update(this->m_state);

    val0_dac->setConstant(0);

    val1_dac->setConstant(pos);
    meas1 = util::meas_fast_chip_out(this);
    error = max(fabs(meas1 - target_pos), error);

    val1_dac->setConstant(neg);
    meas2 = util::meas_fast_chip_out(this);
    error = max(fabs(meas2 - target_neg), error);

    N_MULT_POINTS_TESTED += 2;
#ifdef DEBUG_MULT_CAL
    sprintf(FMTBUF,"zero-in0 code=%d error=%f targ=(%f,%f) meas=(%f,%f)\n", i, error,
            target_neg,target_pos,meas1,meas2);
    print_info(FMTBUF);
#endif
    cutil::update_calib_table(out_table,error,1,i);
  }
  this->m_state.port_cal[out0Id] = out_table.state[0];

  sprintf(FMTBUF,"BEST-zero-out code=%d error=%f\n", out_table.state[0], out_table.loss);
  print_info(FMTBUF);


  cutil::update_calib_table(table_bias,out_table.loss,3,
                            this->m_state.port_cal[in0Id],
                            this->m_state.port_cal[in1Id],
                            this->m_state.port_cal[out0Id]
                            );
  sprintf(FMTBUF,"BEST-ZERO targ=%f/%f nmos=%d pmos=%d port_cal=(%d,%d,%d) loss=%f",
          target_pos,target_neg,this->m_state.nmos,this->m_state.pmos,
          table_bias.state[0],table_bias.state[1],table_bias.state[2],
          table_bias.loss);
  print_info(FMTBUF);
  ref_to_tileout.setConn();
}


void Fabric::Chip::Tile::Slice::Multiplier::calibrateHelperFindVgaBiasCodes(cutil::calib_table_t & table_bias, int stride,
                                                                         Dac* val0_dac,
                                                                         Dac* ref_dac,
                                                                         int bounds[6],
                                                                         float pos,
                                                                         float target_pos,
                                                                         float neg,
                                                                         float target_neg){

  Fabric::Chip::Connection ref_to_tileout =
    Fabric::Chip::Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0);
  ref_to_tileout.brkConn();

  cutil::calib_table_t in0_table = cutil::make_calib_table();
  this->m_state.port_cal[in0Id] = 32;
  this->m_state.port_cal[in1Id] = 32;
  this->m_state.port_cal[out0Id] = 32;
  for(int i=0; i < MAX_BIAS_CAL; i += 1){
    float error = 0.0;
    float meas1,meas2;

    this->m_state.port_cal[in0Id] = i;
    this->update(this->m_state);

    val0_dac->setConstant(0);

    this->setGain(pos);
    meas1 = util::meas_fast_chip_out(this);
    error = max(fabs(meas1 - target_pos),error);

    this->setGain(neg);
    meas2 = util::meas_fast_chip_out(this);
    error = max(fabs(meas2 - target_neg),error);
    N_MULT_POINTS_TESTED += 2;
#ifdef DEBUG_MULT_CAL 
    sprintf(FMTBUF,"zero-in0 code=%d error=%f targ=(%f,%f) meas=(%f,%f)\n", i, error,
            target_neg,target_pos,meas1,meas2);
    print_info(FMTBUF);
#endif
    cutil::update_calib_table(in0_table,error,1,i);
  }
  sprintf(FMTBUF,"BEST-zero-in0 code=%d error=%f\n", in0_table.state[0], in0_table.loss);
  print_info(FMTBUF);

  this->m_state.port_cal[in0Id] = in0_table.state[0];


  cutil::calib_table_t out_table = cutil::make_calib_table();
  val0_dac->setConstant(0);
  for(int i=0; i < MAX_BIAS_CAL; i += 1){
    float error = 0.0;
    float meas1,meas2;
    this->m_state.port_cal[out0Id] = i;
    this->update(this->m_state);

    this->setGain(pos);
    meas1 = util::meas_fast_chip_out(this);
    error = max(fabs(meas1 - target_pos),error);

    this->setGain(neg);
    meas2 = util::meas_fast_chip_out(this);
    error = max(fabs(meas2 - target_neg),error);
    N_MULT_POINTS_TESTED += 2;

#ifdef DEBUG_MULT_CAL
    sprintf(FMTBUF,"zero-out code=%d error=%f targ=(%f,%f) meas=(%f,%f)\n", i, error,
            target_neg,target_pos,meas1,meas2);
    print_info(FMTBUF);
#endif
    cutil::update_calib_table(out_table,error,1,i);
  }
  sprintf(FMTBUF,"BEST-zero-out code=%d error=%f\n", out_table.state[0], out_table.loss);
  print_info(FMTBUF);

  this->m_state.port_cal[out0Id] = out_table.state[0];

  cutil::update_calib_table(table_bias,out_table.loss,3,
                            this->m_state.port_cal[in0Id],
                            this->m_state.port_cal[in1Id],
                            this->m_state.port_cal[out0Id]
                            );
  sprintf(FMTBUF,"BEST-ZERO targ=%f/%f nmos=%d pmos=%d port_cal=(%d,%d,%d) loss=%f",
          target_pos,target_neg,this->m_state.nmos,this->m_state.pmos,
          table_bias.state[0],table_bias.state[1],table_bias.state[2],
          table_bias.loss);
  print_info(FMTBUF);
  ref_to_tileout.setConn();
}


void Fabric::Chip::Tile::Slice::Multiplier::calibrate(calib_objective_t obj) {
  if(this->m_state.vga){
    this->calibrateVga(obj);
  }
  else{
    this->calibrateMult(obj);
  }
}

void Fabric::Chip::Tile::Slice::Multiplier::calibrateVga (calib_objective_t obj) {
  mult_state_t codes_self = this->m_state;

  int next_slice1 = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  int next_slice2 = (slice_to_int(parentSlice->sliceId) + 2) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice2].dac;
  Dac * val0_dac = parentSlice->dac;

  mult_state_t state_mult = this->m_state;
  dac_state_t state_dac_val0 = val0_dac->m_state;
  dac_state_t state_dac_ref = ref_dac->m_state;

  N_MULT_POINTS_TESTED = 0;
  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_mult_conns(calib,this);
  cutil::buffer_dac_conns(calib,ref_dac);
  cutil::buffer_dac_conns(calib,val0_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile
                              ->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

  Connection dac0_to_in0 = Connection (val0_dac->out0, this->in0);
  Connection mult_to_tileout = Connection (this->out0, parentSlice->tileOuts[3].in0);
	Connection tileout_to_chipout = Connection ( parentSlice->tileOuts[3].out0,
                                               parentSlice->parentTile
                                               ->parentChip->tiles[3].slices[2].chipOutput->in0 );
  Fabric::Chip::Connection ref_to_tileout =
    Fabric::Chip::Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0);


  float min_gain_code,n_gain_codes;
  min_gain_code=0;
  n_gain_codes=MAX_GAIN_CAL;

  ref_dac->setRange(util::range_to_dac_range(this->m_state.range[out0Id]));

  float target_pos = 0.0;
  float target_neg = 0.0;
  float target_pos_in = 0.0;
  float target_neg_in = 0.0;
  float dummy,dac_out0;
  int bias_bounds[6];
  bias_bounds[0] = bias_bounds[2] = bias_bounds[4] = 0;
  bias_bounds[1] = bias_bounds[3] = bias_bounds[5] = MAX_BIAS_CAL;

  val0_dac->setRange(util::range_to_dac_range(this->m_state.range[in0Id]));
  fast_calibrate_dac(val0_dac);
  val0_dac->setConstant(0.0);
  dac_out0 = val0_dac->fastMeasureValue(dummy);
  target_pos_in = 1.0;
  this->setGain(target_pos_in);
  target_pos = computeOutput(this->m_state, dac_out0, 0.0);
  target_neg_in = -1.0;
  this->setGain(target_neg_in);
  target_neg = computeOutput(this->m_state, dac_out0, 0.0);


  mult_to_tileout.setConn();
  ref_to_tileout.setConn();
	tileout_to_chipout.setConn();
  dac0_to_in0.setConn();

  cutil::calib_table_t calib_table = cutil::make_calib_table();
  /*nmos, gain_cal, port_cal in0,in1,out*/
  for(int nmos=0; nmos < MAX_NMOS; nmos += 1){
    this->m_state.nmos = nmos;
    this->m_state.pmos = 3;
    this->m_state.gain_cal = 32;
    cutil::calib_table_t table_bias = cutil::make_calib_table();
    this->calibrateHelperFindVgaBiasCodes(table_bias, 8,
                                       val0_dac,
                                       ref_dac,
                                       bias_bounds,
                                       target_pos_in,
                                       target_pos,
                                       target_neg_in,
                                       target_neg);

    this->m_state.port_cal[in0Id] = table_bias.state[0];
    this->m_state.port_cal[in1Id] = table_bias.state[1];
    this->m_state.port_cal[out0Id] = table_bias.state[2];


    for(int pmos=0; pmos < MAX_PMOS; pmos += 1){
      float loss = 0.0;
      this->m_state.pmos = pmos;
      int gain_points[3] = {32,0,63};
      float losses[3];
      for(int i=0; i < 3; i += 1){
        this->m_state.gain_cal = gain_points[i];
        this->update(this->m_state);
        losses[i] = getLoss(obj,val0_dac,NULL,ref_dac,false);
        sprintf(FMTBUF,"pn nmos=%d, pmos=%d, gain=%d loss=%f",
                nmos,pmos,gain_points[i],losses[i]);
        print_info(FMTBUF);
      }
      int best_code;
      loss = util::find_best_gain_cal(gain_points,losses,3,best_code);
      this->m_state.gain_cal = best_code;
      cutil::update_calib_table(calib_table,loss,6,
                                nmos,
                                pmos,
                                this->m_state.port_cal[in0Id],
                                this->m_state.port_cal[in1Id],
                                this->m_state.port_cal[out0Id],
                                this->m_state.gain_cal);
      sprintf(FMTBUF,"best-pm nmos=%d pmos=%d port_cal=(%d,%d,%d) gain_cal=%d loss=%f",
              calib_table.state[0],
              calib_table.state[1],
              calib_table.state[2],
              calib_table.state[3],
              calib_table.state[4],
              calib_table.state[5],
              calib_table.loss);
      print_info(FMTBUF);

    }
  }

  this->m_state.nmos = calib_table.state[0];
  this->m_state.pmos = calib_table.state[1];
  this->m_state.port_cal[in0Id] = calib_table.state[2];
  this->m_state.port_cal[in1Id] = calib_table.state[3];
  this->m_state.port_cal[out0Id] = calib_table.state[4];
  this->m_state.gain_cal = calib_table.state[5];
  // fine grain bias calculation
  cutil::calib_table_t table_bias = cutil::make_calib_table();
  int stride=4;
  this->calibrateHelperFindVgaBiasCodes(table_bias, stride,
                                     val0_dac,
                                     ref_dac,
                                     bias_bounds,
                                     target_pos_in,
                                     target_pos,
                                     target_neg_in,
                                     target_neg);
  bias_bounds[0] = max(table_bias.state[0]-4,0);
  bias_bounds[1] = min(table_bias.state[0]+4,MAX_BIAS_CAL);
  bias_bounds[2] = max(table_bias.state[1]-4,0);
  bias_bounds[3] = min(table_bias.state[1]+4,MAX_BIAS_CAL);
  bias_bounds[4] = max(table_bias.state[2]-4,0);
  bias_bounds[5] = min(table_bias.state[2]+4,MAX_BIAS_CAL);
  this->calibrateHelperFindVgaBiasCodes(table_bias, 1,
                                     val0_dac,
                                     ref_dac,
                                     bias_bounds,
                                     target_pos_in,
                                     target_pos,
                                     target_neg_in,
                                     target_neg);

  this->m_state.port_cal[in0Id] = table_bias.state[0];
  this->m_state.port_cal[in1Id] = table_bias.state[1];
  this->m_state.port_cal[out0Id] = table_bias.state[2];
  // do a thorough search for best nmos code.
  for(int gain_cal=0; gain_cal < MAX_GAIN_CAL; gain_cal+=1){
    this->m_state.gain_cal = gain_cal;
    this->update(this->m_state);
    float loss = getLoss(obj,val0_dac,NULL,ref_dac,false);
    cutil::update_calib_table(calib_table,loss,6,
                              this->m_state.nmos,
                              this->m_state.pmos,
                              this->m_state.port_cal[in0Id],
                              this->m_state.port_cal[in1Id],
                              this->m_state.port_cal[out0Id],
                              gain_cal);
    sprintf(FMTBUF,"nmos=%d pmos=%d port_cal=(%d,%d,%d) gain_cal=%d loss=%f",
            this->m_state.nmos,
            this->m_state.pmos,
            this->m_state.port_cal[in0Id],
            this->m_state.port_cal[in1Id],
            this->m_state.port_cal[out0Id],
            this->m_state.gain_cal,
            loss);
    print_info(FMTBUF);
  }

  val0_dac->update(state_dac_val0);
  ref_dac->update(state_dac_ref);
  this->update(state_mult);
  tileout_to_chipout.brkConn();
  mult_to_tileout.brkConn();
  cutil::restore_conns(calib);

  print_info("set state");
  this->m_state.nmos = calib_table.state[0];
  this->m_state.pmos = calib_table.state[1];
  this->m_state.port_cal[in0Id] = calib_table.state[2];
  this->m_state.port_cal[in1Id] = calib_table.state[3];
  this->m_state.port_cal[out0Id] = calib_table.state[4];
  this->m_state.gain_cal = calib_table.state[5];

  sprintf(FMTBUF,"BEST nmos=%d pmos=%d port_cal=(%d,%d,%d) gain_cal=%d loss=%f",
          this->m_state.nmos,
          this->m_state.pmos,
          this->m_state.port_cal[in0Id],
          this->m_state.port_cal[in1Id],
          this->m_state.port_cal[out0Id],
          this->m_state.gain_cal,
          calib_table.loss);
  print_info(FMTBUF);
  sprintf(FMTBUF,"Tested Points: %d\n", N_MULT_POINTS_TESTED);
  print_info(FMTBUF);
}

void Fabric::Chip::Tile::Slice::Multiplier::calibrateMult(calib_objective_t obj) {
  mult_state_t codes_self = this->m_state;

  int next_slice1 = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  int next_slice2 = (slice_to_int(parentSlice->sliceId) + 2) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice2].dac;
  Dac * val0_dac = parentSlice->dac;
  Dac * val1_dac = parentSlice->parentTile->slices[next_slice1].dac;

  mult_state_t state_mult = this->m_state;
  dac_state_t state_dac_val0 = val0_dac->m_state;
  dac_state_t state_dac_val1 = val1_dac->m_state;
  dac_state_t state_dac_ref = ref_dac->m_state;

  N_MULT_POINTS_TESTED = 0;
  cutil::calibrate_t calib;
  cutil::initialize(calib);
  cutil::buffer_mult_conns(calib,this);
  cutil::buffer_dac_conns(calib,ref_dac);
  cutil::buffer_dac_conns(calib,val0_dac);
  cutil::buffer_dac_conns(calib,val1_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,parentSlice->parentTile
                              ->parentChip->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

  Connection dac0_to_in0 = Connection (val0_dac->out0, this->in0);
  Connection dac1_to_in1 = Connection (val1_dac->out0, this->in1);
  Connection mult_to_tileout = Connection (this->out0, parentSlice->tileOuts[3].in0);
	Connection tileout_to_chipout = Connection ( parentSlice->tileOuts[3].out0,
                                               parentSlice->parentTile
                                               ->parentChip->tiles[3].slices[2].chipOutput->in0 );
  Fabric::Chip::Connection ref_to_tileout =
    Fabric::Chip::Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0);


  float min_gain_code=32,n_gain_codes=1;
  ref_dac->setRange(util::range_to_dac_range(this->m_state.range[out0Id]));

  float target_pos = 0.0;
  float target_neg = 0.0;
  float target_pos_in = 0.0;
  float target_neg_in = 0.0;
  float dummy,dac_out0,dac_out1;
  int bias_bounds[6];
  bias_bounds[0] = bias_bounds[2] = bias_bounds[4] = 0;
  bias_bounds[1] = bias_bounds[3] = bias_bounds[5] = MAX_BIAS_CAL;

  // 0.5*0*2.0
  fast_calibrate_dac(val0_dac);
  fast_calibrate_dac(val1_dac);
  val0_dac->setRange(util::range_to_dac_range(this->m_state.range[in0Id]));
  val1_dac->setRange(util::range_to_dac_range(this->m_state.range[in1Id]));
  
  val0_dac->setConstant(0.0);
  dac_out0 = val0_dac->fastMeasureValue(dummy);
  target_pos_in = 0.5;
  val1_dac->setConstant(target_pos_in);
  dac_out1 = val1_dac->fastMeasureValue(dummy);
  target_pos = computeOutput(this->m_state, dac_out0, dac_out1);
  target_neg_in = -0.5;
  val1_dac->setConstant(target_neg_in);
  dac_out1 = val1_dac->fastMeasureValue(dummy);
  target_neg = computeOutput(this->m_state, dac_out0, dac_out1);


  mult_to_tileout.setConn();
  ref_to_tileout.setConn();
	tileout_to_chipout.setConn();
  dac0_to_in0.setConn();
  dac1_to_in1.setConn();

  cutil::calib_table_t calib_table = cutil::make_calib_table();
  /*nmos, gain_cal, port_cal in0,in1,out*/
  for(int nmos=0; nmos < MAX_NMOS; nmos += 1){
      this->m_state.nmos = nmos;
      this->m_state.pmos = 3;
      this->m_state.gain_cal = 32; 
      this->update(this->m_state);
      cutil::calib_table_t table_bias = cutil::make_calib_table();
      this->calibrateHelperFindMultBiasCodes(table_bias, 8,
                                         val0_dac,
                                         val1_dac,
                                         ref_dac,
                                         bias_bounds,
                                         target_pos_in,
                                         target_pos,
                                         target_neg_in,
                                         target_neg);

    for(int pmos=0; pmos < MAX_PMOS; pmos += 1){
      this->m_state.pmos = pmos;
      this->update(this->m_state);
      
      this->m_state.port_cal[in0Id] = table_bias.state[0];
      this->m_state.port_cal[in1Id] = table_bias.state[1];
      this->m_state.port_cal[out0Id] = table_bias.state[2];
      float loss = getLoss(obj,val0_dac,val1_dac,ref_dac,false);
      sprintf(FMTBUF,"pn nmos=%d, pmos=%d, loss=%f",
              nmos,pmos,loss);
      print_info(FMTBUF);

      cutil::update_calib_table(calib_table,loss,6,
                                nmos,
                                pmos,
                                this->m_state.port_cal[in0Id],
                                this->m_state.port_cal[in1Id],
                                this->m_state.port_cal[out0Id],
                                this->m_state.gain_cal);
    }
    sprintf(FMTBUF,"BEST-pm nmos=%d pmos=%d port_cal=(%d,%d,%d) gain_cal=%d loss=%f",
            calib_table.state[0],
            calib_table.state[1],
            calib_table.state[2],
            calib_table.state[3],
            calib_table.state[4],
            calib_table.state[5],
            calib_table.loss);
    print_info(FMTBUF);
  }

  this->m_state.nmos = calib_table.state[0];
  this->m_state.pmos = calib_table.state[1];
  this->m_state.port_cal[in0Id] = calib_table.state[2];
  this->m_state.port_cal[in1Id] = calib_table.state[3];
  this->m_state.port_cal[out0Id] = calib_table.state[4];
  this->m_state.gain_cal = calib_table.state[5];
  // fine grain bias calculation
  cutil::calib_table_t table_bias = cutil::make_calib_table();
  this->calibrateHelperFindMultBiasCodes(table_bias, 4,
                                     val0_dac,
                                     val1_dac,
                                     ref_dac,
                                     bias_bounds,
                                     target_pos_in,
                                     target_pos,
                                     target_neg_in,
                                     target_neg);
  bias_bounds[0] = max(table_bias.state[0]-4,0);
  bias_bounds[1] = min(table_bias.state[0]+4,MAX_BIAS_CAL);
  bias_bounds[2] = max(table_bias.state[1]-4,0);
  bias_bounds[3] = min(table_bias.state[1]+4,MAX_BIAS_CAL);
  bias_bounds[4] = max(table_bias.state[2]-4,0);
  bias_bounds[5] = min(table_bias.state[2]+4,MAX_BIAS_CAL);
  this->calibrateHelperFindMultBiasCodes(table_bias, 1,
                                     val0_dac,
                                     val1_dac,
                                     ref_dac,
                                     bias_bounds,
                                     target_pos_in,
                                     target_pos,
                                     target_neg_in,
                                     target_neg);

  this->m_state.port_cal[in0Id] = table_bias.state[0];
  this->m_state.port_cal[in1Id] = table_bias.state[1];
  this->m_state.port_cal[out0Id] = table_bias.state[2];

  val0_dac->update(state_dac_val0);
  val1_dac->update(state_dac_val1);
  ref_dac->update(state_dac_ref);
  this->update(state_mult);
  tileout_to_chipout.brkConn();
  mult_to_tileout.brkConn();
  cutil::restore_conns(calib);

  print_info("set state");
  this->m_state.nmos = calib_table.state[0];
  this->m_state.pmos = calib_table.state[1];
  this->m_state.port_cal[in0Id] = calib_table.state[2];
  this->m_state.port_cal[in1Id] = calib_table.state[3];
  this->m_state.port_cal[out0Id] = calib_table.state[4];
  this->m_state.gain_cal = calib_table.state[5];

  sprintf(FMTBUF,"BEST nmos=%d pmos=%d port_cal=(%d,%d,%d) gain_cal=%d loss=%f",
          this->m_state.nmos,
          this->m_state.pmos,
          this->m_state.port_cal[in0Id],
          this->m_state.port_cal[in1Id],
          this->m_state.port_cal[out0Id],
          this->m_state.gain_cal,
          calib_table.loss);
  print_info(FMTBUF);
  sprintf(FMTBUF,"Tested Points: %d\n", N_MULT_POINTS_TESTED);
  print_info(FMTBUF);
}
