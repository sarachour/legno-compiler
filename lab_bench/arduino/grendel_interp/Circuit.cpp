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


void exec_command(Fabric * fab, cmd_t& cmd, float* inbuf){
  cmd_use_dac_t dacd;
  cmd_use_mult_t multd;
  cmd_use_fanout_t fod;
  cmd_use_integ_t integd;
  cmd_use_lut_t lutd;
  cmd_write_lut_t wrlutd;
  cmd_use_adc_t adcd;
  cmd_connection_t connd;
  block_code_t state;
  serializable_profile_t result;
  uint8_t byteval;
  char buf[32];
  Fabric::Chip::Tile::Slice* slice;
  Fabric::Chip::Tile::Slice::Dac* dac;
  Fabric::Chip::Tile::Slice::Multiplier * mult;
  Fabric::Chip::Tile::Slice::Fanout * fanout;
  Fabric::Chip::Tile::Slice::Integrator* integ;
  Fabric::Chip::Tile::Slice::LookupTable* lut;
  Fabric::Chip::Tile::Slice::ChipAdc * adc;
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* src;
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* dst;
  switch(cmd.type){
  case cmd_type_t::USE_ADC:
    adcd = cmd.data.adc;
    adc = common::get_slice(fab,adcd.loc)->adc;
    adc->setEnable(true);
    adc->setRange((range_t) adcd.in_range);
    comm::response("enabled adc",0);
    break;
  case cmd_type_t::USE_DAC:
    dacd = cmd.data.dac;
    dac = common::get_slice(fab,dacd.loc)->dac;
    dac->setEnable(true);
    dac->setInv(dacd.inv);
    dac->setRange((range_t) dacd.out_range);
    dac->setSource((dac_source_t) dacd.source);
    if(dacd.source == DSRC_MEM){
      dac->setConstant(dacd.value);
    }
    comm::response("enabled dac",0);
    break;

  case cmd_type_t::USE_MULT:
    // multiplier doesn't actually support inversion
    // multiplier uses dac from same row.
    multd = cmd.data.mult;
    mult = common::get_mult(fab,multd.loc);
    mult->setEnable(true);
    mult->setVga(multd.use_coeff);
    mult->setRange(in0Id,(range_t) multd.in0_range);
    mult->setRange(out0Id,(range_t) multd.out_range);
    if(not multd.use_coeff){
      mult->setRange(in1Id,(range_t) multd.in1_range);
    }
    else{
      mult->setGain(multd.coeff);
    }
    comm::response("enabled mult",0);
    break;
  case cmd_type_t::USE_FANOUT:
    fod = cmd.data.fanout;
    fanout = common::get_fanout(fab,fod.loc);
    fanout->setEnable(true);
    fanout->setRange((range_t) fod.in_range);
    fanout->setInv(out0Id,fod.inv[0]);
    fanout->setInv(out1Id,fod.inv[1]);
    fanout->setInv(out2Id,fod.inv[2]);
    fanout->setThird(fod.third);
    comm::response("enabled fanout",0);
    break;

  case cmd_type_t::USE_INTEG:
    integd = cmd.data.integ;
    integ = common::get_slice(fab,integd.loc)->integrator;
    integ->setEnable(true);
    integ->setException( integd.debug == 1 ? true : false);
    integ->setInv(integd.inv);
    integ->setRange(in0Id,(range_t) integd.in_range);
    integ->setRange(out0Id,(range_t) integd.out_range);
    integ->setInitial(integd.value);
    comm::response("enabled integ",0);
    break;
  case cmd_type_t::GET_INTEG_STATUS:
    integ = common::get_slice(fab,cmd.data.circ_loc)->integrator;
    comm::response("retrieved integ exception",1);
    comm::data(integ->getException() ? "1" : "0", "i");
    break;
  case cmd_type_t::GET_ADC_STATUS:
    adc = common::get_slice(fab,cmd.data.circ_loc)->adc;
    comm::response("retrieved  lut exception",1);
    sprintf(buf,"%d",adc->getStatusCode());
    comm::data(buf, "i");
    break;
  case cmd_type_t::USE_LUT:
    lutd = cmd.data.lut;
    lut = common::get_slice(fab,lutd.loc)->lut;
    lut->setSource((lut_source_t) lutd.source);
    comm::response("use lut",0);
    break;
  case cmd_type_t::WRITE_LUT:
    wrlutd = cmd.data.write_lut;
    lut = common::get_slice(fab,wrlutd.loc)->lut;
    for(int data_idx=0; data_idx < wrlutd.n; data_idx+=1){
      byteval = min(round(inbuf[data_idx]*128.0 + 128.0),255);
      if(inbuf[data_idx] < -1.0 || inbuf[data_idx] > 1.0){
        comm::error("lut value not in <-1,1>");
      }
      lut->setLut(wrlutd.offset+data_idx,byteval);
    }
    comm::response("write lut",0);
    break;
  case cmd_type_t::DISABLE_DAC:
    dac = common::get_slice(fab,cmd.data.circ_loc)->dac;
    dac->setEnable(false);
    comm::response("disabled dac",0);
    break;
  case cmd_type_t::DISABLE_ADC:
    adc = common::get_slice(fab,cmd.data.circ_loc)->adc;
    adc->setEnable(false);
    comm::response("disabled adc",0);
    break;
  case cmd_type_t::DISABLE_LUT:
    lut = common::get_slice(fab,cmd.data.circ_loc)->lut;
    //lut->setEnable(false);
    comm::response("disabled lut",0);
    break;
  case cmd_type_t::DISABLE_MULT:
    multd = cmd.data.mult;
    mult = common::get_mult(fab,multd.loc);
    mult->setEnable(false);
    comm::response("disabled mult",0);
    break;
  case cmd_type_t::DISABLE_FANOUT:
    fod = cmd.data.fanout;
    fanout = common::get_fanout(fab,fod.loc);
    fanout->setEnable(false);
    comm::response("disabled fanout",0);
    break;
  case cmd_type_t::DISABLE_INTEG:
    integd = cmd.data.integ;
    integ = common::get_slice(fab,integd.loc)->integrator;
    integ->setEnable(false);
    comm::response("disabled integ",0);
    break;
  case cmd_type_t::CONNECT:
    connd = cmd.data.conn;
    src = common::get_output_port(fab,connd.src_blk,connd.src_loc);
    dst = common::get_input_port(fab,connd.dst_blk,connd.dst_loc);
    Fabric::Chip::Connection(src,dst).setConn();
    comm::response("connected",0);
    break;
  case cmd_type_t::BREAK:
    connd = cmd.data.conn;
    src = common::get_output_port(fab,connd.src_blk,connd.src_loc);
    dst = common::get_input_port(fab,connd.dst_blk,connd.dst_loc);
    Fabric::Chip::Connection(src,dst).brkConn();
    comm::response("disconnected",0);
    break;

  case cmd_type_t::CHARACTERIZE:
    print_log("characterizing...");
    result.result = calibrate::measure(fab,
                                       cmd.data.prof.blk,
                                       cmd.data.prof.loc,
                                       cmd.data.prof.mode,
                                       cmd.data.prof.in0,
                                       cmd.data.prof.in1);
    print_log("getting codes...");
    calibrate::get_codes(fab,
                         cmd.data.calib.blk,
                         cmd.data.calib.loc,
                         state);
    print_log("done");
    comm::response("characterization terminated",1);
    sprintf(FMTBUF,"%d",sizeof(state)+sizeof(result.result)+2);
    comm::data(FMTBUF,"I");
    comm::payload();
    Serial.print(sizeof(result.result));
    Serial.print(" ");
    Serial.print(sizeof(state));
    for(unsigned int i=0; i < sizeof(result.result); i+=1){
      Serial.print(" ");
      Serial.print(result.charbuf[i]);
    }
    for(unsigned int i=0; i < sizeof(state); i+=1){
      Serial.print(" ");
      Serial.print(state.charbuf[i]);
    }
    Serial.println("");
    break;


  case cmd_type_t::CALIBRATE:
    print_log("calibrating...");
    calibrate::calibrate(fab,
                         cmd.data.calib.blk,
                         cmd.data.calib.loc,
                         cmd.data.calib.calib_obj);
    print_log("getting codes...");
    calibrate::get_codes(fab,
                         cmd.data.calib.blk,
                         cmd.data.calib.loc,
                         state);
    print_log("done");
    comm::response("calibration terminated",1);
    sprintf(FMTBUF,"%d",sizeof(state)+2);
    comm::data(FMTBUF,"I");
    comm::payload();
    Serial.print(sizeof(state));
    Serial.print(" ");
    Serial.print(true ? 1 : 0);
    for(int i=0; i < sizeof(state); i+=1){
      Serial.print(" ");
      Serial.print(state.charbuf[i]);
    }
    Serial.println("");
    break;

  case cmd_type_t::GET_STATE:
    calibrate::get_codes(fab,
                         cmd.data.state.blk,
                         cmd.data.state.loc,
                         state);
    comm::response("returning codes",1);
    sprintf(FMTBUF,"%d",sizeof(state)+1);
    comm::data(FMTBUF,"I");
    comm::payload();
    Serial.print(sizeof(state));
    for(int i=0; i < sizeof(state); i+=1){
      Serial.print(" ");
      Serial.print(state.charbuf[i]);
    }
    Serial.println("");
    break;
  case cmd_type_t::SET_STATE:
    memcpy(state.charbuf,
           cmd.data.state.data,
           sizeof(block_code_t));
    calibrate::set_codes(fab,
                         cmd.data.state.blk,
                         cmd.data.state.loc,
                         state);
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


