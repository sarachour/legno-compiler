#include "AnalogLib.h"
#include "Circuit.h"
#include "Experiment.h"
#include "Comm.h"

namespace circ {

  void print_lut_source(lut_source_t src){
    switch(src){
    case LSRC_CONTROLLER: Serial.print("ctrl"); break;
    case LSRC_EXTERN : Serial.print("extern"); break;
    case LSRC_ADC0 : Serial.print("lut0"); break;
    case LSRC_ADC1 : Serial.print("lut1"); break;
    default: Serial.print("<?>"); break;
    }
  }
  void print_dac_source(dac_source_t src){
    switch(src){
    case DSRC_MEM: Serial.print("mem"); break;
    case DSRC_EXTERN : Serial.print("extern"); break;
    case DSRC_LUT0 : Serial.print("lut0"); break;
    case DSRC_LUT1 : Serial.print("lut1"); break;
    default: Serial.print("<?>"); break;
    }
  }
  

  void print_block(uint8_t type){
    switch(type){
    case block_type::TILE_DAC:
      Serial.print("dac");
      break;
    case block_type::CHIP_INPUT:
      Serial.print("chip_in");
      break;
    case block_type::CHIP_OUTPUT:
      Serial.print("chip_out");
      break;
    case block_type::TILE_INPUT:
      Serial.print("tile_in");
      break;
    case block_type::TILE_OUTPUT:
      Serial.print("tile_out");
    break;
    case block_type::MULT:
      Serial.print("mult");
      break;
    case block_type::INTEG:
      Serial.print("integ");
      break;
    case block_type::FANOUT:
      Serial.print("fanout");
      break;
    case block_type::LUT:
      Serial.print("lut");
      break;
    case block_type::TILE_ADC:
      Serial.print("adc");
      break;
    default:
      Serial.print("unknown<");
      Serial.print(type);
      Serial.print(">");
      break;
    }
  }
  void print_block_loc(block_loc_t& inst){
    print_block(inst.block);
    Serial.print("(");
    Serial.print(inst.chip);
    Serial.print(",");
    Serial.print(inst.tile);
    Serial.print(",");
    Serial.print(inst.slice);
    Serial.print(",");
    Serial.print(inst.idx);
    Serial.print(")");
  }
  void print_port_loc(port_loc_t& loc){
    print_block_loc(loc.inst);
    Serial.print(".");
    Serial.print(util::ifc_to_string(loc.port));
     
  }

#define range_to_str(code) (code == HI_RANGE ? "h" : (code == MED_RANGE ? "m" : (code == LOW_RANGE ? "l" : "?")))

#define sign_to_str(code) (code ? "-" : "+")


#define print3(e1,e2,e3) {                        \
    Serial.print("(");                          \
    Serial.print(e1);                           \
    Serial.print(",");                          \
    Serial.print(e2);                           \
    Serial.print(",");                          \
    Serial.print(e3);                           \
    Serial.print(")");                          \
}
#define print2(e1,e2) { \
  Serial.print("("); \
  Serial.print(e1); \
  Serial.print(","); \
  Serial.print(e2); \
  Serial.print(")");                            \
}

  void print_state(block_type_t blk, block_code_t state){
    switch(blk){
    case block_type_t::TILE_DAC:
      Serial.print("enable=");
      Serial.print(state.dac.enable);
      Serial.print(" inv=");
      Serial.print(state.dac.inv);
      Serial.print(" range=");
      Serial.print(range_to_str(state.dac.range));
      Serial.print(" source=");
      print_dac_source(state.dac.source);
      Serial.print(" pmos=");
      Serial.print(state.dac.pmos);
      Serial.print(" nmos=");
      Serial.print(state.dac.nmos);
      Serial.print(" gain_cal=");
      Serial.print(state.dac.gain_cal);
      Serial.print(" code=");
      Serial.print(state.dac.const_code);
      break;

    case block_type_t::MULT:
      Serial.print("enable=");
      Serial.print(state.mult.enable);
      Serial.print(" range=");
      print3(range_to_str(state.mult.range[in0Id]),
             range_to_str(state.mult.range[in1Id]),
             range_to_str(state.mult.range[out0Id]));
      Serial.print(" pmos=");
      Serial.print(state.mult.pmos);
      Serial.print(" nmos=");
      Serial.print(state.mult.nmos);
      Serial.print(" gain_cal=");
      Serial.print(state.mult.gain_cal);
      Serial.print(" port_cal=");
      print3(state.mult.port_cal[in0Id],
             state.mult.port_cal[in1Id],
             state.mult.port_cal[out0Id]);
      Serial.print(" gain_code=");
      Serial.print(state.mult.gain_code);
      break;

    case block_type_t::INTEG:
      Serial.print("enable=");
      Serial.print(state.integ.enable);
      Serial.print(" exception=");
      Serial.print(state.integ.exception);
      Serial.print(" inv=");
      Serial.print(sign_to_str(state.integ.inv));
      Serial.print(" range=");
      print2(range_to_str(state.integ.range[in0Id]),
             range_to_str(state.integ.range[out0Id]));
      Serial.print(" pmos=");
      Serial.print(state.integ.pmos);
      Serial.print(" nmos=");
      Serial.print(state.integ.nmos);
      Serial.print(" gain_cal=");
      Serial.print(state.integ.gain_cal);
      Serial.print(" cal_enable=");
      print2(state.integ.cal_enable[in0Id],
             state.integ.cal_enable[out0Id]);
      Serial.print(" port_cal=");
      print2(state.integ.port_cal[in0Id],
             state.integ.port_cal[out0Id]);
      Serial.print(" ic_code=");
      Serial.print(state.integ.ic_code);
      break;

    case block_type_t::FANOUT:
      Serial.print("enable=");
      Serial.print(state.fanout.enable);
      Serial.print(" third=");
      Serial.print(state.fanout.third);
      Serial.print(" range=");
      Serial.print(range_to_str(state.fanout.range));
      Serial.print(" pmos=");
      Serial.print(state.fanout.pmos);
      Serial.print(" nmos=");
      Serial.print(state.fanout.nmos);
      Serial.print(" port_cal=");
      print3(state.fanout.port_cal[out0Id],
             state.fanout.port_cal[out1Id],
             state.fanout.port_cal[out2Id]);
      break;

    case block_type_t::TILE_ADC:
      Serial.print("test_en=");
      Serial.print(state.adc.test_en);
      Serial.print(" test_adc=");
      Serial.print(state.adc.test_adc);
      Serial.print(" test_i2v=");
      Serial.print(state.adc.test_i2v);
      Serial.print(" test_rs=");
      Serial.print(state.adc.test_rs);
      Serial.print(" test_rsinc=");
      Serial.print(state.adc.test_rsinc);
      Serial.print(" enable=");
      Serial.print(state.adc.enable);
      Serial.print(" pmos=");
      Serial.print(state.adc.pmos);
      Serial.print(" nmos=");
      Serial.print(state.adc.nmos);
      Serial.print(" pmos2=");
      Serial.print(state.adc.pmos2);
      Serial.print(" i2v_cal=");
      Serial.print(state.adc.i2v_cal);
      Serial.print(" upper_fs=");
      Serial.print(state.adc.upper_fs);
      Serial.print(" upper=");
      Serial.print(state.adc.upper);
      Serial.print(" lower_fs=");
      Serial.print(state.adc.lower_fs);
      Serial.print(" lower=");
      Serial.print(state.adc.lower);
      Serial.print(" range=");
      Serial.print(range_to_str(state.adc.range));
      break;
    case block_type_t::LUT:
      Serial.print("source=");
      print_lut_source(state.lut.source);
      break;

    default:
      Serial.println("<generic-state>");
      break;
    }
  }
  void print_command(cmd_t& cmd){
    comm::print_header();
    switch(cmd.type){
    case cmd_type_t::GET_BLOCK_STATUS:
      Serial.print("get block status ");
      print_block_loc(cmd.data.get_status.inst);
      break;
    case cmd_type_t::WRITE_LUT:
      Serial.print("write lut ");
      print_block_loc(cmd.data.write_lut.inst);
      break;
    case cmd_type_t::DISABLE:
      Serial.print("disable ");
      print_block_loc(cmd.data.disable.inst);
      break;
    case cmd_type_t::CONNECT:
      Serial.print("conn ");
      print_port_loc(cmd.data.conn.src);
      Serial.print("->");
      print_port_loc(cmd.data.conn.dst);
      break;
    case cmd_type_t::BREAK:
      Serial.print("break ");
      print_port_loc(cmd.data.conn.src);
      Serial.print("<->");
      print_port_loc(cmd.data.conn.dst);
      break;
    case cmd_type_t::CALIBRATE:
      Serial.print("calibrate ");
      print_block_loc(cmd.data.calib.inst);
      Serial.print(" mode=");
      Serial.print(cmd.data.calib.calib_obj);
      break;

    case cmd_type_t::PROFILE:
      Serial.print("profile ");
      print_block_loc(cmd.data.calib.inst);
      break;

    case cmd_type_t::GET_STATE:
      Serial.print("get_state ");
      print_block_loc(cmd.data.get_state.inst);
      break;

    case cmd_type_t::SET_STATE:
      Serial.print("set_state ");
      print_block_loc(cmd.data.set_state.inst);
      Serial.print(" ");
      print_state(cmd.data.set_state.inst.block,
                  cmd.data.set_state.state);
      break;

    case cmd_type_t::DEFAULTS:
      Serial.print("defaults");
      break;

    default:
      Serial.print(cmd.type);
      Serial.print(" <unimpl print circuit>");
      break;
    }
    Serial.println("");
  }
}

namespace experiment {


  void debug_command(experiment_t* expr, Fabric* fab, cmd_t& cmd, float * inbuf){
    switch(cmd.type){
    case cmd_type_t::RESET:
      comm::response("[dbg] resetted",0);
      break;
    case cmd_type_t::RUN:
      comm::response("[dbg] ran",0);
      break;
    case cmd_type_t::USE_ANALOG_CHIP:
      comm::response("[dbg] use_analog_chip=true",0);
      break;
    case cmd_type_t::USE_OSC:
      comm::response("[dbg] enable_trigger=true",0);
      break;
    case cmd_type_t::SET_SIM_TIME:
      comm::response("[dbg] set simulation time",0);
      break;
    }
  }

  void print_command(cmd_t& cmd, float* inbuf){
    comm::print_header();
    switch(cmd.type){
    case cmd_type_t::SET_SIM_TIME:
      Serial.print("set_sim_time sim=");
      Serial.print(cmd.args.floats[0]);
      Serial.print(" period=");
      Serial.println(cmd.args.floats[1]);
      Serial.print(" osc=");
      Serial.println(cmd.args.floats[2]);
      break;

    case cmd_type_t::USE_OSC:
      Serial.println("use_osc");
      break;

    case cmd_type_t::USE_ANALOG_CHIP:
      Serial.println("use_analog_chip");
      break;

    case cmd_type_t::RESET:
      Serial.println("reset");
      break;

    case cmd_type_t::RUN:
      Serial.println("run");
      break;

    default:
      Serial.print(cmd.type);
      Serial.print(" ");
      Serial.print(cmd.args.ints[0]);
      Serial.print(" ");
      Serial.print(cmd.args.ints[1]);
      Serial.print(" ");
      Serial.print(cmd.args.ints[2]);
      Serial.println(" <unimpl print experiment>");
      break;
    }
  }


}
