#include "AnalogLib.h"
#include "assert.h"
#include "calib_util.h"

void Fabric::Chip::Tile::Slice::Fanout::measureZero(float &out0bias,
                                                    float &out1bias,
                                                    float &out2bias){
  // backup and clobber state.
  cutil::calibrate_t calib;
  fanout_code_t codes_fan = this->m_codes;
  cutil::initialize(calib);
  cutil::buffer_fanout_conns(calib,this);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,
                              parentSlice->parentTile->parentChip
                              ->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);
  Connection tileout_to_chipout = Connection (parentSlice->tileOuts[3].out0,
                                              parentSlice->parentTile->parentChip
                                              ->tiles[3].slices[2].chipOutput->in0);
  Connection conn_out0 = Connection (this->out0,parentSlice->tileOuts[3].in0);
  Connection conn_out1 = Connection (this->out1,parentSlice->tileOuts[3].in0);
  Connection conn_out2 = Connection (this->out2,parentSlice->tileOuts[3].in0);
  tileout_to_chipout.setConn();

  conn_out0.setConn();
  out0bias = util::meas_chip_out(this);
  conn_out0.brkConn();
  conn_out1.setConn();
  out1bias = util::meas_chip_out(this);
  conn_out1.brkConn();
  conn_out2.setConn();
  out2bias = util::meas_chip_out(this);
  conn_out2.brkConn();
  tileout_to_chipout.brkConn();

  this->update(codes_fan);
  cutil::restore_conns(calib);
}
float Fabric::Chip::Tile::Slice::Fanout::getLoss(calib_objective_t obj,
                Fabric::Chip::Tile::Slice::Dac * val_dac,
                Fabric::Chip::Tile::Slice::Dac * ref_dac,
                ifc outId
                )
{
  switch(obj){
  case CALIB_MINIMIZE_ERROR:
    return calibrateMinError(val_dac,ref_dac,outId);
    break;
  case CALIB_MAXIMIZE_DELTA_FIT:
    return calibrateMaxDeltaFit(val_dac,ref_dac,outId);
    break;
  case CALIB_FAST:
    return calibrateFast(val_dac,ref_dac,outId);
    break;
  default:
    error("unknown obj function");
  }
}


void Fabric::Chip::Tile::Slice::Fanout::calibrate(calib_objective_t obj){
  //backup state
  cutil::calibrate_t calib;
  cutil::initialize(calib);

  int next_slice = (slice_to_int(parentSlice->sliceId) + 1) % 4;
  Dac * ref_dac = parentSlice->parentTile->slices[next_slice].dac;
  Dac * val_dac = parentSlice->dac;
  fanout_code_t codes_fanout = m_codes;
  dac_code_t codes_ref_dac = ref_dac->m_codes;
  dac_code_t codes_val_dac = val_dac->m_codes;
  cutil::buffer_fanout_conns(calib,this);
  cutil::buffer_dac_conns(calib,ref_dac);
  cutil::buffer_dac_conns(calib,val_dac);
  cutil::buffer_tileout_conns(calib,&parentSlice->tileOuts[3]);
  cutil::buffer_chipout_conns(calib,
                              parentSlice->parentTile->parentChip
                              ->tiles[3].slices[2].chipOutput);
  cutil::break_conns(calib);

  //setup circuit
  Connection tileout_to_chipout = Connection (parentSlice->tileOuts[3].out0,
                                          parentSlice->parentTile->parentChip
                                          ->tiles[3].slices[2].chipOutput->in0);
  Connection conn_out0 = Connection (this->out0,parentSlice->tileOuts[3].in0);
  Connection conn_out1 = Connection (this->out1,parentSlice->tileOuts[3].in0);
  Connection conn_out2 = Connection (this->out2,parentSlice->tileOuts[3].in0);
  Fabric::Chip::Connection ref_to_tileout =
    Fabric::Chip::Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0);
  Fabric::Chip::Connection val_to_fanout =
    Fabric::Chip::Connection ( val_dac->out0, this->in0);

  // always enable third output so all of them can be calibrated
  this->setThird(true);
  //enable dacs
  ref_dac->setEnable(true);
  val_dac->setEnable(true);
  ref_to_tileout.setConn();
  val_to_fanout.setConn();
  tileout_to_chipout.setConn();

  // nmos code doesn't change much
  this->m_codes.nmos = 0;
  // bind best bias code for out0
  cutil::calib_table_t calib_table = cutil::make_calib_table();
  // coarse grain global search: 3375 combos
  for(int bias_cal0=0; bias_cal0 < MAX_BIAS_CAL; bias_cal0+=4){
    this->m_codes.port_cal[out0Id] = bias_cal0;
    for(int bias_cal1=0; bias_cal1 < MAX_BIAS_CAL; bias_cal1+=4){
      this->m_codes.port_cal[out1Id] = bias_cal1;
      for(int bias_cal2=0; bias_cal2 < MAX_BIAS_CAL; bias_cal2+=4){
        this->m_codes.port_cal[out2Id] = bias_cal2;
        update(this->m_codes);
        conn_out0.setConn();
        float loss = getLoss(CALIB_FAST,val_dac,ref_dac,out0Id);
        conn_out0.brkConn();
        conn_out1.setConn();
        loss = max(loss,getLoss(CALIB_FAST,val_dac,ref_dac,out1Id));
        conn_out1.brkConn();
        conn_out2.setConn();
        loss = max(loss,getLoss(CALIB_FAST,val_dac,ref_dac,out2Id));
        conn_out2.brkConn();
        cutil::update_calib_table(calib_table,loss,4,
                                  bias_cal0,
                                  bias_cal1,
                                  bias_cal2,
                                  this->m_codes.nmos
                                  );
      }
    }

    sprintf(FMTBUF, "CRS nmos=%d bias_codes=(%d,%d,%d) loss=%f",
            calib_table.state[3],
            calib_table.state[0],
            calib_table.state[1],
            calib_table.state[2],
            calib_table.loss
            );
    print_info(FMTBUF);
  }

  // fine grain local search: 343 combos
  int coarse_bias_cal0 = calib_table.state[0];
  int coarse_bias_cal1 = calib_table.state[1];
  int coarse_bias_cal2= calib_table.state[2];
  for(int i=-3; i < 4; i += 1){
    int bias_cal0 = coarse_bias_cal0 + i;
    if(bias_cal0 < 0 || bias_cal0 >= MAX_BIAS_CAL)
      continue;
    this->m_codes.port_cal[out0Id] = bias_cal0;

    for(int j=-3; j < 4; j += 1){
      int bias_cal1 = coarse_bias_cal1 + j;
      if(bias_cal1 < 0 || bias_cal1 >= MAX_BIAS_CAL)
        continue;
      this->m_codes.port_cal[out1Id] = bias_cal1;

      for(int k=-3; k < 4; k += 1){
        int bias_cal2 = coarse_bias_cal2 + k;
        if(bias_cal2 < 0 || bias_cal2 >= MAX_BIAS_CAL)
          continue;
        update(this->m_codes);
        conn_out0.setConn();
        float loss = getLoss(CALIB_FAST,val_dac,ref_dac,out0Id);
        conn_out0.brkConn();
        conn_out1.setConn();
        loss = max(loss,getLoss(CALIB_FAST,val_dac,ref_dac,out1Id));
        conn_out1.brkConn();
        conn_out2.setConn();
        loss = max(loss,getLoss(CALIB_FAST,val_dac,ref_dac,out2Id));
        conn_out2.brkConn();
        cutil::update_calib_table(calib_table,loss,4,
                                  bias_cal0,
                                  bias_cal1,
                                  bias_cal2,
                                  this->m_codes.nmos
                                  );
      }
    }
    sprintf(FMTBUF, "FINE nmos=%d bias_codes=(%d,%d,%d) loss=%f",
            calib_table.state[3],
            calib_table.state[0],
            calib_table.state[1],
            calib_table.state[2],
            calib_table.loss
            );
    print_info(FMTBUF);
  }
  ref_to_tileout.brkConn();
  val_to_fanout.brkConn();
  tileout_to_chipout.brkConn();
  cutil::restore_conns(calib);
  ref_dac->m_codes = codes_ref_dac;
  val_dac->m_codes = codes_val_dac;
  this->m_codes = codes_fanout;
  //set best hidden codes
  int best_nmos=0;
  int best_loss=0;
  best_loss = calib_table.loss;
  this->m_codes.port_cal[out0Id] = calib_table.state[0];
  this->m_codes.port_cal[out1Id] = calib_table.state[1];
  this->m_codes.port_cal[out2Id] = calib_table.state[2];
  this->m_codes.nmos = calib_table.state[3];
  update(this->m_codes);
  return;
}

#define CALIB_NPTS 4
const float TEST_POINTS[CALIB_NPTS] = {0,-0.5,-1,1};


float Fabric::Chip::Tile::Slice::Fanout::calibrateMaxDeltaFit(Fabric::Chip::Tile::Slice::Dac * val_dac,
                                                              Fabric::Chip::Tile::Slice::Dac * ref_dac,
                                                              ifc out_id) {
  float gains[CALIB_NPTS];
  float bias = 0.0;
  int m = 0;
  for(int i=0; i < CALIB_NPTS; i += 1){
    float mean,dummy;
    bool measure_steady_state = false;
    val_dac->setConstant(TEST_POINTS[i]);
    float in_val = val_dac->fastMeasureValue(dummy);
    float target =Fabric::Chip::Tile::Slice::Fanout::computeOutput(this->m_codes,
                                                                   out_id,
                                                                   in_val);
    bool succ = cutil::measure_signal_robust(this, ref_dac, target,
                                             measure_steady_state,
                                             mean,
                                             dummy);
    if(succ){
      if(TEST_POINTS[i] == 0.0){
        bias = fabs(mean-target);
      }
      else{
        gains[m] = mean/target;
        m += 1;
      }
    }
  }
  float gain_mean,gain_variance;
  util::distribution(gains,m,
                     gain_mean,
                     gain_variance);
  float loss = max(sqrt(gain_variance),fabs(bias));
  return loss;
}
float Fabric::Chip::Tile::Slice::Fanout::calibrateMinError(Fabric::Chip::Tile::Slice::Dac * val_dac,
                                                           Fabric::Chip::Tile::Slice::Dac * ref_dac,
                                                           ifc out_id) {
  float loss_total = 0;
  int total = 0;
  for(int i=0; i < CALIB_NPTS; i += 1){
    float mean,dummy;
    bool measure_steady_state = false;
    val_dac->setConstant(TEST_POINTS[i]);
    float in_val = val_dac->fastMeasureValue(dummy);
    float target =Fabric::Chip::Tile::Slice::Fanout::computeOutput(this->m_codes,
                                                                   out_id,
                                                                   in_val);
    bool succ = cutil::measure_signal_robust(this, ref_dac, target,
                                             measure_steady_state,
                                             mean,
                                             dummy);
    if(succ){
      loss_total = fabs(target-mean);
      total += 1;
    }
  }
  if(total > 0)
    return loss_total/total;
  else
    error("no valid points");

  return 0.0;
}

float Fabric::Chip::Tile::Slice::Fanout::calibrateFast(Fabric::Chip::Tile::Slice::Dac * val_dac,
                    Fabric::Chip::Tile::Slice::Dac * ref_dac,
                    ifc out_id){
  Fabric::Chip::Connection val_to_fanout =
    Fabric::Chip::Connection ( val_dac->out0, this->in0);
  Fabric::Chip::Connection ref_to_tileout =
    Fabric::Chip::Connection ( ref_dac->out0, parentSlice->tileOuts[3].in0);
  val_to_fanout.brkConn();
  ref_to_tileout.brkConn();
  float meas = util::meas_chip_out(this);
  val_to_fanout.setConn();
  ref_to_tileout.setConn();
  return fabs(meas);
}
