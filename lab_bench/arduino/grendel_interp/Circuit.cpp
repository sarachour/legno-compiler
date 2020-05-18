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

void write_struct_bytes(const char * bytes, unsigned int n){
  sprintf(FMTBUF,"%d",n+1);
  comm::data(FMTBUF,"I");
  comm::payload();
  Serial.print(n);
  for(unsigned int i = 0; i < n; i+=1){
    Serial.print(" ");
    Serial.print(bytes[i]);
  }
  Serial.println("");
}


void exec_command(Fabric * fab, cmd_t& cmd, float* inbuf){
  cmd_write_lut_t wrlutd;
  cmd_connect_t connd;
  block_state_t state;
  profile_t result;
  uint8_t byteval;
  char buf[32];
  Fabric::Chip::Tile::Slice::LookupTable* lut;
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* src;
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* dst;
  switch(cmd.type){
  
  case cmd_type_t::GET_BLOCK_STATUS:
    comm::response("retrieved block status",1);
    sprintf(buf,"%d",
            common::get_block_status(fab, cmd.data.get_status.inst));
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
    common::disable_block(fab,cmd.data.disable.inst);
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
    result = calibrate::measure(fab,
                                cmd.data.prof.spec);
    comm::response("completed!",1);
    write_struct_bytes((const char *) &result, sizeof(result));
    break;

  case cmd_type_t::CALIBRATE:
    print_log("calibrating...");
    calibrate::calibrate(fab,
                         cmd.data.calib.inst,
                         cmd.data.calib.calib_obj);
    print_log("getting codes...");
    calibrate::get_state(fab,
                         cmd.data.calib.inst,
                         state);
    print_log("done");
    comm::response("calibration terminated",1);
    write_struct_bytes((const char *) &state, sizeof(state));
    break;

  case cmd_type_t::GET_STATE:
    calibrate::get_state(fab,
                         cmd.data.get_state.inst,
                         state);
    comm::response("returning codes",1);
    write_struct_bytes((const char *) &state, sizeof(state));
    break;
  case cmd_type_t::SET_STATE:
    calibrate::set_state(fab,
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


