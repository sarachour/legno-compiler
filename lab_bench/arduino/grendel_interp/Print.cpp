#include "AnalogLib.h"
#include "Circuit.h"
#include "Experiment.h"
#include "Comm.h"

namespace circ {



  void print_command(cmd_t& cmd){
    comm::print_header();
    switch(cmd.type){
    case cmd_type_t::GET_BLOCK_STATUS:
      Serial.print("get block status ");
      sprintf_block_inst(cmd.data.get_status.inst,FMTBUF);
      Serial.print(FMTBUF);
      break;
    case cmd_type_t::WRITE_LUT:
      Serial.print("write lut ");
      sprintf_block_inst(cmd.data.write_lut.inst,FMTBUF);
      Serial.print(FMTBUF);
      break;
    case cmd_type_t::DISABLE:
      Serial.print("disable ");
      sprintf_block_inst(cmd.data.disable.inst,FMTBUF);
      Serial.print(FMTBUF);
      break;
    case cmd_type_t::CONNECT:
      Serial.print("conn ");
      sprintf_block_port(cmd.data.conn.src,FMTBUF);
      Serial.print(FMTBUF);
      Serial.print("->");
      sprintf_block_port(cmd.data.conn.dst,FMTBUF);
      Serial.print(FMTBUF);
      break;
    case cmd_type_t::BREAK:
      Serial.print("break ");
      sprintf_block_port(cmd.data.conn.src,FMTBUF);
      Serial.print(FMTBUF);
      Serial.print("->");
      sprintf_block_port(cmd.data.conn.dst,FMTBUF);
      Serial.print(FMTBUF);
      break;
    case cmd_type_t::CALIBRATE:
      Serial.print("calibrate ");
      sprintf_block_inst(cmd.data.calib.inst,FMTBUF);
      Serial.print(FMTBUF);
      Serial.print(" mode=");
      Serial.print(cmd.data.calib.calib_obj);
      break;

    case cmd_type_t::PROFILE:
      Serial.print("profile ");
      sprintf_block_inst(cmd.data.prof.spec.inst,FMTBUF);
      Serial.print(FMTBUF);
      break;

    case cmd_type_t::GET_STATE:
      Serial.print("get_state ");
      sprintf_block_inst(cmd.data.get_state.inst,FMTBUF);
      Serial.print(FMTBUF);
      break;

    case cmd_type_t::SET_STATE:
      Serial.print("set_state ");
      sprintf_block_inst(cmd.data.set_state.inst,FMTBUF);
      Serial.print(FMTBUF);
      Serial.print(" ");
      sprintf_block_state(cmd.data.set_state.inst.block,
                          cmd.data.set_state.state,
                          FMTBUF);
      Serial.print(FMTBUF);
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
