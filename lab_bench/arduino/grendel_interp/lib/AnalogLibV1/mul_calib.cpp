#include "AnalogLib.h"
#include "fu.h"
#include "mul.h"
#include "calib_util.h"
#include <float.h>

#define CALIB_NPTS 4
#define TOTAL_NPTS (1 + CALIB_NPTS*CALIB_NPTS)
const float TEST0_POINTS[CALIB_NPTS] = {-0.75,0.75,0.5,0.0};
const float TEST1_MULT_POINTS[CALIB_NPTS] = {-0.75,0.75,0.5,0.0};
const float TEST1_VGA_POINTS[CALIB_NPTS] = {-0.75,0.75,0.5,0.0};

float Fabric::Chip::Tile::Slice::Multiplier::getLoss(calib_objective_t obj,
                                                     Dac * val0_dac,
                                                     Dac * val1_dac,
                                                     Dac * ref_dac,
                                                     bool ignore_bias){
  float loss;
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
  if(this->m_codes.vga){
    return calibrateMaxDeltaFitVga(val0_dac, ref_dac,ignore_bias);
  }
  else{
    return calibrateMaxDeltaFitMult(val0_dac, val1_dac, ref_dac,ignore_bias);
  }
}


float Fabric::Chip::Tile::Slice::Multiplier::calibrateMinError(Dac * val0_dac,
                                                               Dac * val1_dac,
                                                               Dac * ref_dac){
  if(this->m_codes.vga){
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
  for(int i=0; i < CALIB_NPTS; i += 1){
    for(int j=0; j < CALIB_NPTS; j += 1){
      float in0 = TEST0_POINTS[i];
      float in1 = TEST1_VGA_POINTS[j];
      val_dac->setConstant(in0);
      this->setGain(in1);
      float target_in0 = val_dac->fastMeasureValue(variance);
      float target_out = this->computeOutput(this->m_codes,
                                             target_in0,
                                             0.0);

      bool succ = cutil::measure_signal_robust(this,
                                            ref_dac,
                                            target_out,
                                            meas_steady,
                                            mean,
                                            variance);
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
  for(int i=0; i < CALIB_NPTS; i += 1){
    for(int j=0; j < CALIB_NPTS; j += 1){
      float in0 = TEST0_POINTS[i];
      float in1 = TEST1_MULT_POINTS[j];
      float variance,mean;
      val0_dac->setConstant(in0);
      val1_dac->setConstant(in1);
      float target_in0 = val0_dac->fastMeasureValue(dummy);
      float target_in1 = val1_dac->fastMeasureValue(dummy);
      float target_out = this->computeOutput(this->m_codes,
                                             target_in0,
                                             target_in1
                                             );

      bool succ = cutil::measure_signal_robust(this,
                                               ref_dac,
                                               target_out,
                                               meas_steady,
                                               mean,
                                               variance);
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
  float observed[TOTAL_NPTS];
  float expected[TOTAL_NPTS];
  float errors[TOTAL_NPTS];
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
  util::linear_regression(expected,errors,npts,
                          gain_mean,bias,rsq,max_error,avg_error);

  // put no emphasis on deviation, because it will not adhere to 1.0
  return cutil::compute_loss(ignore_bias ? 0.0 : bias,max_std,
                             avg_error,
                             1.0 + gain_mean,
                             this->m_codes.range[out0Id], 
                             0.0, 10.0);
}
float Fabric::Chip::Tile::Slice::Multiplier::calibrateMaxDeltaFitVga(Dac * val_dac,
                                                                     Dac * ref_dac,
                                                                     bool ignore_bias){
  int npts;
  float observed[TOTAL_NPTS];
  float expected[TOTAL_NPTS];
  float errors[TOTAL_NPTS];
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
  return cutil::compute_loss(ignore_bias ? 0.0 : bias,highest_std,
                             avg_error,
                             1.0+gain_mean,
                             this->m_codes.range[out0Id],
                             0.003,
                             10.0);
}
float Fabric::Chip::Tile::Slice::Multiplier::calibrateMinErrorVga(Dac * val_dac,
                                                                  Dac * ref_dac){
  int npts;
  float observed[TOTAL_NPTS];
  float expected[TOTAL_NPTS];
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
  float observed[TOTAL_NPTS];
  float expected[TOTAL_NPTS];
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

void Fabric::Chip::Tile::Slice::Multiplier::calibrateHelperFindBiasCodes(cutil::calib_table_t & table_bias, int stride,
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
  this->m_codes.port_cal[in0Id] = 32;
  this->m_codes.port_cal[in1Id] = 32;
  this->m_codes.port_cal[out0Id] = 32;
  for(int i=0; i < MAX_BIAS_CAL; i += 1){
    this->m_codes.port_cal[in0Id] = i;
    this->update(this->m_codes);
    float error = 0.0;
    if(this->m_codes.vga){
      this->setGain(pos);
      error += fabs(util::meas_fast_chip_out(this) - target_pos);
      this->setGain(neg);
      error += fabs(util::meas_fast_chip_out(this) - target_neg);
    }
    else{
      val1_dac->setConstant(pos);
      error += fabs(util::meas_fast_chip_out(this) - target_pos);
      val1_dac->setConstant(neg);
      error += fabs(util::meas_fast_chip_out(this) - target_neg);
    }
    cutil::update_calib_table(in0_table,error,1,i);
  }
  this->m_codes.port_cal[in0Id] = in0_table.state[0];
  if(!this->m_codes.vga){
    cutil::calib_table_t in1_table = cutil::make_calib_table();
    for(int i=0; i < MAX_BIAS_CAL; i += 1){
      this->m_codes.port_cal[in1Id] = i;
      this->update(this->m_codes);
      float error = 0.0;
      val1_dac->setConstant(pos);
      error += fabs(util::meas_fast_chip_out(this) - target_pos);
      val1_dac->setConstant(neg);
      error += fabs(util::meas_fast_chip_out(this) - target_neg);
      cutil::update_calib_table(in1_table,error,1,i);
    }
    this->m_codes.port_cal[in1Id] = in1_table.state[0];
  }
  cutil::calib_table_t out_table = cutil::make_calib_table();
  for(int i=0; i < MAX_BIAS_CAL; i += 1){
    this->m_codes.port_cal[out0Id] = i;
    this->update(this->m_codes);
    float error = 0.0;
    if(this->m_codes.vga){
      this->setGain(pos);
      error += fabs(util::meas_fast_chip_out(this) - target_pos);
      this->setGain(neg);
      error += fabs(util::meas_fast_chip_out(this) - target_neg);
    }
    else{
      val1_dac->setConstant(pos);
      error += fabs(util::meas_fast_chip_out(this) - target_pos);
      val1_dac->setConstant(neg);
      error += fabs(util::meas_fast_chip_out(this) - target_neg);
    }
    cutil::update_calib_table(out_table,error,1,i);
  }
  this->m_codes.port_cal[out0Id] = out_table.state[0];

  cutil::update_calib_table(table_bias,0.0,3,
                            this->m_codes.port_cal[in0Id],
                            this->m_codes.port_cal[in1Id],
                            this->m_codes.port_cal[out0Id]
                            );
  sprintf(FMTBUF,"BEST-ZERO targ=%f/%f nmos=%d pmos=%d port_cal=(%d,%d,%d) loss=%f",
          target_pos,target_neg,this->m_codes.nmos,this->m_codes.pmos,
          table_bias.state[0],table_bias.state[1],table_bias.state[2],
          table_bias.loss);
  print_info(FMTBUF);
  ref_to_tileout.setConn();
}



void Fabric::Chip::Tile::Slice::Multiplier::calibrate (calib_objective_t obj) {
  mult_code_t codes_self = m_codes;

  int next_slice1 = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  int next_slice2 = (slice_to_int(parentSlice->sliceId) + 2) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice2].dac;
  Dac * val0_dac = parentSlice->dac;
  Dac * val1_dac = parentSlice->parentTile->slices[next_slice1].dac;

  mult_code_t codes_mult = m_codes;
  dac_code_t codes_dac_val0 = val0_dac->m_codes;
  dac_code_t codes_dac_val1 = val1_dac->m_codes;
  dac_code_t codes_dac_ref = ref_dac->m_codes;

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
  if(this->m_codes.vga){
    min_gain_code=0;
    n_gain_codes=MAX_GAIN_CAL;
  }

  ref_dac->setRange(util::range_to_dac_range(this->m_codes.range[out0Id]));

  float target_pos = 0.0;
  float target_neg = 0.0;
  float dummy,dac_out0,dac_out1;
  int bias_bounds[6];
  bias_bounds[0] = bias_bounds[2] = bias_bounds[4] = 0;
  bias_bounds[1] = bias_bounds[3] = bias_bounds[5] = MAX_BIAS_CAL;

  if(this->m_codes.vga){
    val0_dac->setRange(util::range_to_dac_range(this->m_codes.range[in0Id]));
    fast_calibrate_dac(val0_dac);
    val0_dac->setConstant(0.0);
    dac_out0 = val0_dac->fastMeasureValue(dummy);
    this->setGain(1.0);
    target_pos = computeOutput(this->m_codes, dac_out0, 0.0);
    this->setGain(-1.0);
    target_neg = computeOutput(this->m_codes, dac_out0, 0.0);

  }
  else{
    fast_calibrate_dac(val0_dac);
    fast_calibrate_dac(val1_dac);
    val0_dac->setRange(util::range_to_dac_range(this->m_codes.range[in0Id]));
    val1_dac->setRange(util::range_to_dac_range(this->m_codes.range[in1Id]));
    val0_dac->setConstant(0.0);
    dac_out0 = val0_dac->fastMeasureValue(dummy);
    val1_dac->setConstant(0.5);
    dac_out1 = val1_dac->fastMeasureValue(dummy);
    target_pos = computeOutput(this->m_codes, dac_out0, dac_out1);
    val1_dac->setConstant(-0.5);
    dac_out1 = val1_dac->fastMeasureValue(dummy);
    target_neg = computeOutput(this->m_codes, dac_out0, dac_out1);
  }


  mult_to_tileout.setConn();
  ref_to_tileout.setConn();
	tileout_to_chipout.setConn();
  dac0_to_in0.setConn();
  if(!this->m_codes.vga)
    dac1_to_in1.setConn();

  cutil::calib_table_t calib_table = cutil::make_calib_table();
  /*nmos, gain_cal, port_cal in0,in1,out*/
  for(int nmos=0; nmos < MAX_NMOS; nmos += 1){
    this->m_codes.nmos = nmos;
    this->m_codes.pmos = 3;
    this->m_codes.gain_cal = 32;
    cutil::calib_table_t table_bias = cutil::make_calib_table();
    this->calibrateHelperFindBiasCodes(table_bias, this->m_codes.vga ? 8 : 4,
                                       val0_dac,
                                       val1_dac,
                                       ref_dac,
                                       bias_bounds,
                                       this->m_codes.vga ? 1.0 : 0.5,
                                       target_pos,
                                       this->m_codes.vga ? -1.0 : -0.5,
                                       target_neg);

    this->m_codes.port_cal[in0Id] = table_bias.state[0];
    this->m_codes.port_cal[in1Id] = table_bias.state[1];
    this->m_codes.port_cal[out0Id] = table_bias.state[2];


    for(int pmos=0; pmos < MAX_PMOS; pmos += 1){
      float loss = 0.0;
      this->m_codes.pmos = pmos;
      if(this->m_codes.vga){
	      int gain_points[3] = {0,32,63};
	      float losses[3];
	      for(int i=0; i < 3; i += 1){
          this->m_codes.gain_cal = gain_points[i];
          this->update(this->m_codes);
          losses[i] = getLoss(obj,val0_dac,val1_dac,ref_dac,false);
          sprintf(FMTBUF,"gain=%d loss=%f",gain_points[i],losses[i]);
	      }
	      int best_code;
	      loss = util::find_best_gain_cal(gain_points,losses,3,best_code);
	      this->m_codes.gain_cal = best_code;
      }
      else{
          this->m_codes.gain_cal = 32;
          this->update(this->m_codes);
          loss = getLoss(obj,val0_dac,val1_dac,ref_dac,false);
      }
      cutil::update_calib_table(calib_table,loss,6,
                                nmos,
                                pmos,
                                this->m_codes.port_cal[in0Id],
                                this->m_codes.port_cal[in1Id],
                                this->m_codes.port_cal[out0Id],
                                this->m_codes.gain_cal
                                );
      sprintf(FMTBUF,"nmos=%d pmos=%d port_cal=(%d,%d,%d) gain_cal=%d loss=%f",
              this->m_codes.nmos,
              this->m_codes.pmos,
              this->m_codes.port_cal[in0Id],
              this->m_codes.port_cal[in1Id],
              this->m_codes.port_cal[out0Id],
              this->m_codes.gain_cal,
              loss);
      print_info(FMTBUF);

    }
  }

  this->m_codes.nmos = calib_table.state[0];
  this->m_codes.pmos = calib_table.state[1];
  this->m_codes.gain_cal = calib_table.state[5];
  // fine grain bias calculation
  cutil::calib_table_t table_bias = cutil::make_calib_table();
  int stride=4;
  this->calibrateHelperFindBiasCodes(table_bias, stride,
                                     val0_dac,
                                     val1_dac,
                                     ref_dac,
                                     bias_bounds,
                                     this->m_codes.vga ? 1.0 : 0.5,
                                     target_pos,
                                     this->m_codes.vga ? -1.0 : -0.5,
                                     target_neg);
  bias_bounds[0] = max(table_bias.state[0]-4,0);
  bias_bounds[1] = min(table_bias.state[0]+4,MAX_BIAS_CAL);
  bias_bounds[3] = max(table_bias.state[1]-4,0);
  bias_bounds[4] = min(table_bias.state[1]+4,MAX_BIAS_CAL);
  bias_bounds[5] = max(table_bias.state[2]-4,0);
  bias_bounds[6] = min(table_bias.state[2]+4,MAX_BIAS_CAL);
  this->calibrateHelperFindBiasCodes(table_bias, 1,
                                     val0_dac,
                                     val1_dac,
                                     ref_dac,
                                     bias_bounds,
                                     this->m_codes.vga ? 1.0 : 0.5,
                                     target_pos,
                                     this->m_codes.vga ? -1.0 : -0.5,
                                     target_neg);

  this->m_codes.port_cal[in0Id] = table_bias.state[0];
  this->m_codes.port_cal[in1Id] = table_bias.state[1];
  this->m_codes.port_cal[out0Id] = table_bias.state[2];
  // do a thorough search for best nmos code.
  for(int gain_cal=min_gain_code; gain_cal < min_gain_code+n_gain_codes; gain_cal+=1){
    this->m_codes.gain_cal = gain_cal;
    this->update(this->m_codes);
    float loss = getLoss(obj,val0_dac,val1_dac,ref_dac,false);
    cutil::update_calib_table(calib_table,loss,6,
                              this->m_codes.nmos,
                              this->m_codes.pmos,
                              this->m_codes.port_cal[in0Id],
                              this->m_codes.port_cal[in1Id],
                              this->m_codes.port_cal[out0Id],
                              gain_cal
                              );
    sprintf(FMTBUF,"nmos=%d pmos=%d port_cal=(%d,%d,%d) gain_cal=%d loss=%f",
            this->m_codes.nmos,
            this->m_codes.pmos,
            this->m_codes.port_cal[in0Id],
            this->m_codes.port_cal[in1Id],
            this->m_codes.port_cal[out0Id],
            this->m_codes.gain_cal,
            loss);
    print_info(FMTBUF);
  }

  val0_dac->update(codes_dac_val0);
  val1_dac->update(codes_dac_val1);
  ref_dac->update(codes_dac_ref);
  this->update(codes_mult);
  tileout_to_chipout.brkConn();
  mult_to_tileout.brkConn();
  //cutil::restore_conns(calib);

  print_info("set state");
  this->m_codes.nmos = calib_table.state[0];
  this->m_codes.pmos = calib_table.state[1];
  this->m_codes.port_cal[in0Id] = calib_table.state[2];
  this->m_codes.port_cal[in1Id] = calib_table.state[3];
  this->m_codes.port_cal[out0Id] = calib_table.state[4];
  this->m_codes.gain_cal = calib_table.state[5];

  sprintf(FMTBUF,"BEST nmos=%d pmos=%d port_cal=(%d,%d,%d) gain_cal=%d loss=%f",
          this->m_codes.nmos,
          this->m_codes.pmos,
          this->m_codes.port_cal[in0Id],
          this->m_codes.port_cal[in1Id],
          this->m_codes.port_cal[out0Id],
          this->m_codes.gain_cal,
          calib_table.loss);
  print_info(FMTBUF);
}
