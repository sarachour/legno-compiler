#include "AnalogLib.h"
#include "fu.h"
#include "connection.h"
#include "calib_util.h"
#include "profile.h"
#include <float.h>


namespace cutil {

  void initialize(calibrate_t& cal){
    cal.success = true;
    cal.nconns = 0;
  }

  calib_table_t make_calib_table(){
    calib_table_t st;
    st.set = false;
    for(int i=0; i < MAX_HIDDEN_STATE; i+=1){
      st.state[i]=0;
    }
    return st;
  }

  void update_calib_table(calib_table_t& table, float new_loss, int n, ...){
    va_list valist;
    va_start(valist, n);
    if(not table.set || table.loss > new_loss){
      table.set = true;
      table.loss = new_loss;
      if(n >= MAX_HIDDEN_STATE){
        error("not enough space in table");
      }
      for(int i=0; i < n; i += 1){
        table.state[i] = va_arg(valist, int);
      }
    }
    va_end(valist);
  }

  float compute_loss(float bias, float noise_std, float pred_err,
                     float gain, range_t range,
                     float deviation_weight, float max_gain){
    float mag = util::range_to_coeff(range);
    float error = max(max(fabs(bias),noise_std),pred_err);
    float pct_deviate = fabs(gain-1.0)/1.0;
    float pct_error = error/mag;
    float loss = pct_error+deviation_weight*pct_deviate;
    if(gain > max_gain){
      loss = 10.0;
    }
    sprintf(FMTBUF,"gain=%f bias=%f pred-err=%f noise=%f mag=%f",
            gain,bias,pred_err,noise_std,mag);
    print_info(FMTBUF);
    sprintf(FMTBUF,"pct-error=%f pct-deviate=%f loss=%f",pct_error,pct_deviate,loss);
    print_info(FMTBUF);
    return loss;
  }

  /*
    measures the initial or steady state of a signal, adjusting the
    reference dac until the measurement is within range.
  */
  bool measure_signal_robust(Fabric::Chip::Tile::Slice::FunctionUnit * fu,
                             Fabric::Chip::Tile::Slice::Dac * ref_dac,
                             float target,
                             bool steady,
                             float& mean,
                             float& variance){
    float delta = 0.0;
    float thresh = 1.3;
    float step = 0.12;
    float measurement = 0;
    float ref_dac_val;
    float targ_dac_val;

    dac_code_t codes_dac = ref_dac->m_codes;

    // configure reference dac to maximize gain
    ref_dac->setRange(fabs(target) > 1.0 ? RANGE_HIGH : RANGE_MED);

    fast_calibrate_dac(ref_dac);
    targ_dac_val = Fabric::Chip::Tile::Slice::Dac
      ::computeInput(ref_dac->m_codes,
                     -target);

    do {
      ref_dac->setConstant(max(min(targ_dac_val,1.0),-1.0));
      if(steady){
        util::meas_steady_chip_out(fu,measurement,variance);
      }
      else{
        util::meas_dist_chip_out(fu,measurement,variance);
      }
      if(fabs(measurement) > thresh){
        delta += measurement < 0 ? -step : step;
        targ_dac_val = Fabric::Chip::Tile::Slice::Dac
                               ::computeInput(ref_dac->m_codes,
                                              -(target+delta));
      }
    } while(fabs(measurement) > thresh &&
            fabs(targ_dac_val) <= 1.0);

    if(fabs(measurement) > thresh){
      sprintf(FMTBUF,
              "could not reduce measurement: thresh=%f meas=%f val=%f", \
              thresh,measurement,targ_dac_val);
      print_info(FMTBUF);
    }
    float dummy;
    ref_dac_val = ref_dac->fastMeasureValue(dummy);
    mean = measurement-ref_dac_val;
    variance = variance;

    ref_dac->update(codes_dac);
    return fabs(measurement) <= thresh;

}



  void buffer_conn(calibrate_t& calib, Fabric::Chip::Connection& conn){
    if(calib.nconns < MAX_CONNS){
      int i = calib.nconns;
      calib.conn_buf[i][0] = conn.sourceIfc;
      calib.conn_buf[i][1] = conn.destIfc;
      calib.nconns += 1;
    }
    else{
      error("ran out of connections.");
    }
  }
  void buffer_conns(calibrate_t& calib,
                    Fabric::Chip::Tile::Slice::FunctionUnit * fo,
                    int n_ins,
                    int n_outs){

    if(n_ins >= 1){
      Fabric::Chip::Connection c_in0 = Fabric::Chip::Connection (fo->in0->userSourceDest,
                                                                 fo->in0);
      if(c_in0.sourceIfc && c_in0.destIfc){
        buffer_conn(calib,c_in0);
      }
    }
    if(n_ins >= 2){
      Fabric::Chip::Connection c_in1 = Fabric::Chip::Connection (fo->in1->userSourceDest,
                                                                 fo->in1);
      if(c_in1.sourceIfc){
        buffer_conn(calib,c_in1);
      }
    }
    if(n_outs >= 1){
      Fabric::Chip::Connection c_out0 = Fabric::Chip::Connection (fo->out0,
                                                                  fo->out0->userSourceDest);
      if(c_out0.destIfc){
        buffer_conn(calib,c_out0);
      }
    }
    if(n_outs >= 2){
      Fabric::Chip::Connection c_out1 = Fabric::Chip::Connection (fo->out1,
                                                                  fo->out1->userSourceDest);
      if(c_out1.destIfc){
        buffer_conn(calib,c_out1);
      }
    }
    if(n_outs >= 3){
      Fabric::Chip::Connection c_out2 = Fabric::Chip::Connection (fo->out2,
                                                                  fo->out2->userSourceDest);
      if(c_out2.destIfc){
        buffer_conn(calib,c_out2);
      }
    }
  }
  void buffer_fanout_conns( calibrate_t& calib,
                            Fabric::Chip::Tile::Slice::Fanout* fu){
    buffer_conns(calib,fu,1,3);
  }
  void buffer_mult_conns( calibrate_t& calib,
                          Fabric::Chip::Tile::Slice::Multiplier* fu){
    buffer_conns(calib,fu,2,1);
  }
  void buffer_dac_conns( calibrate_t& calib,
                         Fabric::Chip::Tile::Slice::Dac* fu){
    buffer_conns(calib,fu,0,1);
  }
  void buffer_tileout_conns( calibrate_t& calib,
                             Fabric::Chip::Tile::Slice::TileInOut* fu){
    buffer_conns(calib,fu,1,1);
  }
  void buffer_adc_conns( calibrate_t& calib,
                             Fabric::Chip::Tile::Slice::ChipAdc * fu){
    buffer_conns(calib,fu,1,0);
  }
  void buffer_integ_conns( calibrate_t& calib,
                            Fabric::Chip::Tile::Slice::Integrator * fu){
    buffer_conns(calib,fu,1,1);
  }
  void buffer_chipin_conns( calibrate_t& calib,
                             Fabric::Chip::Tile::Slice::ChipInput * fu){
    buffer_conns(calib,fu,1,1);
  }
  void buffer_chipout_conns( calibrate_t& calib,
                            Fabric::Chip::Tile::Slice::ChipOutput * fu){
    buffer_conns(calib,fu,1,0);
  }
  void break_conns(calibrate_t& calib){
    for(int i=0; i < calib.nconns; i+=1){
      Fabric::Chip::Connection c = Fabric::Chip::Connection(calib.conn_buf[i][0],
                                                            calib.conn_buf[i][1]);
      c.brkConn();
    }
  }
  void restore_conns(calibrate_t& calib){
    for(int i=0; i < calib.nconns; i+=1){
      Fabric::Chip::Connection c = Fabric::Chip::Connection(calib.conn_buf[i][0],
                                                            calib.conn_buf[i][1]);
      c.setConn();
    }
  }

}
