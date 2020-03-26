//#define _DUE
#include "AnalogLib.h"
#include "Circuit.h"
#include "Calibrate.h"
#include "Comm.h"
#include "Common.h"
#include "calib_util.h"
#include "profile.h"
#include <assert.h>

char HCDC_DEMO_BOARD = 6;
//char HCDC_DEMO_BOARD = 4;


namespace circ {


Fabric* setup_board(){
  Fabric* fabric = new Fabric();
  return fabric;
}

void write_block_state(block_code_t& state){
  sprintf(FMTBUF,"%d",sizeof(state)+2);
  comm::data(FMTBUF,"I");
  comm::payload();
  Serial.print(sizeof(state));
  Serial.print(" ");
  Serial.print(true ? 1 : 0);
  for(unsigned int i=0; i < sizeof(state); i+=1){
    Serial.print(" ");
    Serial.print(state.charbuf[i]);
  }
  Serial.println("");
}

int get_block_status(Fabric* fab, block_loc_t blk){
  switch(blk.block){
  case INTEG:
    return common::get_slice(fab,blk)->integrator->getException() ? 1 : 0;
  case TILE_ADC:
    return common::get_slice(fab,blk)->adc->getStatusCode();
  default:
    return 0;
  }

}
  void disable_block(Fabric* fab, block_loc_t blk){
  Fabric::Chip::Tile::Slice* slice;
  slice = common::get_slice(fab,blk);
  switch(blk.block){
  case INTEG:
    slice->integrator->setEnable(false);
    break;
  case TILE_DAC:
    slice->dac->setEnable(false);
    break;
  case TILE_ADC:
    slice->adc->setEnable(false);
    break;
  case MULT:
    slice->muls[blk.idx].setEnable(false);
    break;
  case FANOUT:
    slice->fans[blk.idx].setEnable(false);
    break;
  default:
    error("cannot disable unknown block");
  }
}
void exec_command(Fabric * fab, cmd_t& cmd, float* inbuf){
  cmd_write_lut_t wrlutd;
  cmd_connect_t connd;
  block_code_t state;
  serializable_profile_t result;
  uint8_t byteval;
  char buf[32];
  Fabric::Chip::Tile::Slice::LookupTable* lut;
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* src;
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* dst;
  switch(cmd.type){
  
  case cmd_type_t::GET_BLOCK_STATUS:
    comm::response("retrieved block status",1);
    sprintf(buf,"%d",get_block_status(fab, cmd.data.get_status.inst));
    comm::data(buf, "i");
    break;
  case cmd_type_t::WRITE_LUT:
    wrlutd = cmd.data.write_lut;
    lut = common::get_slice(fab,wrlutd.inst)->lut;
    for(int data_idx=0; data_idx < wrlutd.n; data_idx+=1){
      byteval = min(round(inbuf[data_idx]*128.0 + 128.0),255);
      if(inbuf[data_idx] < -1.0 || inbuf[data_idx] > 1.0){
        comm::error("lut value not in <-1,1>");
      }
      lut->setLut(wrlutd.offset+data_idx,byteval);
    }
    comm::response("write lut",0);
    break;
  case cmd_type_t::DISABLE:
    disable_block(fab,cmd.data.disable.inst);
    comm::response("disabled block",0);
    break;
  case cmd_type_t::CONNECT:
    connd = cmd.data.conn;
    src = common::get_output_port(fab,connd.src);
    dst = common::get_input_port(fab,connd.dst);
    Fabric::Chip::Connection(src,dst).setConn();
    comm::response("connected",0);
    break;
  case cmd_type_t::BREAK:
    connd = cmd.data.conn;
    src = common::get_output_port(fab,connd.src);
    dst = common::get_input_port(fab,connd.dst);
    Fabric::Chip::Connection(src,dst).brkConn();
    comm::response("disconnected",0);
    break;

  case cmd_type_t::PROFILE:
    print_log("profiling...");
    result.result = calibrate::measure(fab,
                                       cmd.data.prof.inst,
                                       cmd.data.prof.spec);
    print_log("getting codes...");
    calibrate::get_codes(fab,
                         cmd.data.calib.inst,
                         state);
    print_log("done");
    comm::response("profiling terminated",1);
    sprintf(FMTBUF,"%d",sizeof(state)+sizeof(result.result)+2);
    comm::data(FMTBUF,"I");
    comm::payload();
    Serial.print(sizeof(result.result));
    Serial.print(" ");
    for(unsigned int i=0; i < sizeof(result.result); i+=1){
      Serial.print(" ");
      Serial.print(result.charbuf[i]);
    }
    Serial.println("");
    break;


  case cmd_type_t::CALIBRATE:
    print_log("calibrating...");
    calibrate::calibrate(fab,
                         cmd.data.calib.inst,
                         cmd.data.calib.calib_obj);
    print_log("getting codes...");
    calibrate::get_codes(fab,
                         cmd.data.calib.inst,
                         state);
    print_log("done");
    comm::response("calibration terminated",1);
    write_block_state(state);
    break;

  case cmd_type_t::GET_STATE:
    calibrate::get_codes(fab,
                         cmd.data.get_state.inst,
                         state);
    comm::response("returning codes",1);
    sprintf(FMTBUF,"%d",sizeof(state)+1);
    comm::data(FMTBUF,"I");
    comm::payload();
    Serial.print(sizeof(state));
    for(unsigned int i=0; i < sizeof(state); i+=1){
      Serial.print(" ");
      Serial.print(state.charbuf[i]);
    }
    Serial.println("");
    break;
  case cmd_type_t::SET_STATE:
    calibrate::set_codes(fab,
                         cmd.data.set_state.inst,
                         cmd.data.set_state.state);
    comm::response("set codes",0);
    break;

  case cmd_type_t::DEFAULTS:
    comm::print_header();
    Serial.println("setting to default");
    fab->defaults();
    comm::response("set defaults",0);
    break;

  default:
    comm::error("unknown command");
    break;
  }
}




}


