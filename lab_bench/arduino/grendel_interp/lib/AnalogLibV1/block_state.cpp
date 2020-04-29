#include "block_state.h"
#include "stdio.h"
#include "util.h"

const char * bool_to_string(uint8_t value){
  if(value){
    return "y";
  }
  else{
    return "n";
  }
}
const char * range_to_string(range_t range){
  switch(range){
  case RANGE_MED: return "m"; break;
  case RANGE_HIGH: return "h"; break;
  case RANGE_LOW: return "l"; break;
  case RANGE_UNKNOWN: return "?"; break;
  }
  return "?";
}
const char * sign_to_string(uint8_t value){
  if(value) return "-";
  else return "+";
}
const char * profile_status_to_string(profile_status_t status){
  switch(status){
  case SUCCESS:
    return "success";
  case FAILED_TO_CALIBRATE:
    return "failed_calibrate";
  default:
    return "unknown-status";
  }

}
const char * profile_type_to_string(profile_type_t type){
  switch(type){
  case INPUT_OUTPUT:
    return "func";
  case INTEG_INITIAL_COND:
    return "integ-ic";
  case INTEG_DERIVATIVE_STABLE:
    return "integ-deriv-stable";
  case INTEG_DERIVATIVE_BIAS:
    return "integ-deriv-bias";
  case INTEG_DERIVATIVE_GAIN:
    return "integ-deriv-gain";
  default:
    return "unknown-type";
  }
}



const char * lut_source_to_string(lut_source_t src){
  switch(src){
  case LSRC_CONTROLLER: return "ctrl"; break;
  case LSRC_EXTERN : return "extern"; break;
  case LSRC_ADC0 : return "lut0"; break;
  case LSRC_ADC1 : return "lut1"; break;
  default: return "unknown-lut-src"; break;
  }
}
const char * dac_source_to_string(dac_source_t src){
  switch(src){
  case DSRC_MEM: return "mem"; break;
  case DSRC_EXTERN : return "extern"; break;
  case DSRC_LUT0 : return "lut0"; break;
  case DSRC_LUT1 : return "lut1"; break;
  default: return "unknown-dac-src"; break;
  }
}


const char * block_type_to_string(uint8_t type){
  switch(type){
  case block_type::TILE_DAC:
    return "dac";
    break;
  case block_type::CHIP_INPUT:
    return "chip_in";
    break;
  case block_type::CHIP_OUTPUT:
    return "chip_out";
    break;
  case block_type::TILE_INPUT:
    return "tile_in";
    break;
  case block_type::TILE_OUTPUT:
    return "tile_out";
  break;
  case block_type::MULT:
    return "mult";
    break;
  case block_type::INTEG:
    return "integ";
    break;
  case block_type::FANOUT:
    return "fanout";
    break;
  case block_type::LUT:
    return "lut";
    break;
  case block_type::TILE_ADC:
    return "adc";
    break;
  default:
    return "unknown-block";
    break;
  }
}
int sprintf_block_inst(block_loc_t& inst, char * buf){
  return sprintf(buf,
                 "%s(%d,%d,%d,%d)",
                 (char*) block_type_to_string(inst.block),
                 inst.chip,inst.tile,inst.slice,inst.idx);
}

int sprintf_block_port(port_loc_t& loc,char * buf){
  int offset = sprintf_block_inst(loc.inst,buf);
  offset += sprintf(&buf[offset],".%s",util::ifc_to_string(loc.port));
  return offset;
}



int sprintf_block_state(block_type_t blk, block_state_t state,char * buf){
  int offset = 0;
  switch(blk){
  case block_type_t::TILE_DAC:
    offset = sprintf(buf,                                                        \
                     "enable=%s inv=%s range=%s source=%s pmos=%d nmos=%d gain_cal=%d code=%d",
                     bool_to_string(state.dac.enable),
                     sign_to_string(state.dac.inv),
                     range_to_string(state.dac.range),
                     dac_source_to_string(state.dac.source),
                     state.dac.pmos, state.dac.nmos,
                     state.dac.gain_cal,
                     state.dac.const_code
                     );
    break;

  case block_type_t::MULT:
    offset = sprintf(buf,                                                        \
                     "enable=%s range=(%s,%s,%s) pmos=%d nmos=%d gain_cal=%d port_cal=(%d,%d,%d) gain_code=%d", \
                     bool_to_string(state.mult.enable),
                     range_to_string(state.mult.range[in0Id]),
                     range_to_string(state.mult.range[in1Id]),
                     range_to_string(state.mult.range[out0Id]),
                     state.mult.pmos, state.mult.nmos,
                     state.mult.gain_cal,
                     state.mult.port_cal[in0Id],
                     state.mult.port_cal[in1Id],
                     state.mult.port_cal[out0Id],
                     state.mult.gain_code
                     );
    break;

  case block_type_t::INTEG:
    offset = sprintf(buf,                                               \
                     "enable=%s exn=%s inv=%s range=(%s,%s) pmos=%d nmos=%d gain_cal=%d cal_enable=(%s,%s) port_cal=(%d,%d) ic_code=%d",
                     bool_to_string(state.integ.enable),
                     bool_to_string(state.integ.exception),
                     sign_to_string(state.integ.inv),
                     range_to_string(state.integ.range[in0Id]),
                     range_to_string(state.integ.range[out0Id]),
                     state.integ.pmos,
                     state.integ.nmos,
                     state.integ.gain_cal,
                     bool_to_string(state.integ.cal_enable[in0Id]),
                     bool_to_string(state.integ.cal_enable[out0Id]),
                     state.integ.port_cal[in0Id],
                     state.integ.port_cal[out0Id],
                     state.integ.ic_code
              );
      break;

    case block_type_t::FANOUT:
      offset = sprintf(buf, \
                       "enable=%s third=%s inv=(%s,%s,%s) range=%s pmos=%d nmos=%d port_cal=(%d,%d,%d)",
                       bool_to_string(state.fanout.enable),
                       bool_to_string(state.fanout.third),
                       sign_to_string(state.fanout.inv[out0Id]),
                       sign_to_string(state.fanout.inv[out1Id]),
                       sign_to_string(state.fanout.inv[out2Id]),
                       range_to_string(state.fanout.range),
                       state.fanout.pmos,
                       state.fanout.nmos,
                       state.fanout.port_cal[out0Id],
                       state.fanout.port_cal[out1Id],
                       state.fanout.port_cal[out2Id]
                       );
      break;


    case block_type_t::TILE_ADC:
      offset=sprintf(buf, "enable=%s range=%s pmos=%d pmos2=%d nmos=%d i2v_cal=%d fs=(u:%d,l:%d) norm=(u=%d,l=%d) test={en:%s,adc:%s,i2v:%s,rs:%s,rsinc:%s}",
                     bool_to_string(state.adc.enable),
                     range_to_string(state.adc.range),
                     state.adc.pmos,
                     state.adc.pmos2,
                     state.adc.nmos,
                     state.adc.i2v_cal,
                     state.adc.upper_fs,
                     state.adc.lower_fs,
                     state.adc.upper,
                     state.adc.lower,
                     bool_to_string(state.adc.test_en),
                     bool_to_string(state.adc.test_adc),
                     bool_to_string(state.adc.test_i2v),
                     bool_to_string(state.adc.test_rs),
                     bool_to_string(state.adc.test_rsinc)
                     );
      break;
    case block_type_t::LUT:
      offset = sprintf(buf,"source=%s", lut_source_to_string(state.lut.source));
      break;

    default:
      offset = sprintf(buf,"<generic-state>");
      break;
    }
  return offset;
}

void sprintf_profile_spec(profile_spec_t& result, char * buf){
  char BUF[256];
  int offset = sprintf_block_state(result.inst.block,result.state,BUF);
  sprintf(buf, "profile-spec state=%s in(%f,%f) out=%s type=%s",
          BUF,
          result.inputs[in0Id],
          result.inputs[in1Id],
          util::ifc_to_string(result.output),
          profile_type_to_string(result.type));
}
void sprintf_profile(profile_t& result, char * buf){
  char BUF[256];
  sprintf_profile_spec(result.spec, BUF);
  sprintf(buf,
          "spec={%s} status=%f mean=%f std=%f",
          BUF,
          profile_status_to_string(result.status),
          result.mean,
          result.stdev);
  
}
