#include "AnalogLib.h"
#include "Circuit.h"
#include "Common.h"
#include "Comm.h"
#include "fu.h"
#include "profile.h"

namespace calibrate {
  calib_objective_t get_objective_max_delta_fit(uint16_t blk){
    switch(blk){
    case circ::block_type_t::FANOUT:
      return CALIB_FAST;
      break;
    case circ::block_type_t::MULT:
      return CALIB_MAXIMIZE_DELTA_FIT;
      break;
    default:
      return CALIB_MINIMIZE_ERROR;
    }
  }
  calib_objective_t get_objective_min_error(uint16_t blk){
    switch(blk){
    case circ::block_type_t::TILE_ADC:
    case circ::block_type_t::FANOUT:
      return CALIB_FAST;
    default:
      return CALIB_MINIMIZE_ERROR;
    }
  }
  calib_objective_t get_objective(uint16_t blk, calib_objective_t macro_obj){
    switch(macro_obj){
    case CALIB_MINIMIZE_ERROR:
      return get_objective_min_error(blk); break;
    case CALIB_MAXIMIZE_DELTA_FIT:
      return get_objective_max_delta_fit(blk); break;
    default:
      error("unsupported macro obj function.");
    }
  }
  profile_t measure(Fabric* fab,
                         uint16_t blk,
                         circ::circ_loc_idx1_t loc,
                         uint8_t mode,
                         float in0,
                         float in1)
  {
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice::ChipAdc * adc;
    Fabric::Chip::Tile::Slice::Dac * dac;
    Fabric::Chip::Tile::Slice::Integrator * integ;
    Fabric::Chip::Tile::Slice::LookupTable * lut;
    switch(blk){
    case circ::block_type_t::FANOUT:
      fanout = common::get_fanout(fab,loc);
      return fanout->measure(mode,in0);
      break;

    case circ::block_type_t::MULT:
      // TODO: indicate if input or output.
      mult = common::get_mult(fab,loc);
      return mult->measure(mode,in0,in1);
      break;

    case circ::block_type_t::TILE_ADC:
      adc = common::get_slice(fab,loc.loc)->adc;
      return adc->measure(in0);
      break;

    case circ::block_type_t::TILE_DAC:
      dac = common::get_slice(fab,loc.loc)->dac;
      return dac->measure(in0);
      break;

    case circ::block_type_t::INTEG:
      integ = common::get_slice(fab,loc.loc)->integrator;
      return integ->measure(mode,in0);
      break;

    case circ::block_type_t::LUT:
      break;
    default:
      comm::error("get_offset_code: unexpected block");
    }
  }

 

  void calibrate(Fabric* fab,
                 uint16_t blk,
                 circ::circ_loc_idx1_t loc,
                 calib_objective_t macro_obj)
  {
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice::ChipAdc * adc;
    Fabric::Chip::Tile::Slice::Dac * dac;
    Fabric::Chip::Tile::Slice::Integrator * integ;
    float max_error = -1.0;
    calib_objective_t obj = get_objective(blk,macro_obj);
    switch(blk){
    case circ::block_type_t::FANOUT:
      fanout = common::get_fanout(fab,loc);
      fanout->calibrate(obj);
      break;

    case circ::block_type_t::MULT:
      // TODO: indicate if input or output.
      mult = common::get_mult(fab,loc);
      mult->calibrate(obj);
      break;

    case circ::block_type_t::TILE_ADC:
      adc = common::get_slice(fab,loc.loc)->adc;
      adc->calibrate(obj);
      break;

    case circ::block_type_t::TILE_DAC:
      dac = common::get_slice(fab,loc.loc)->dac;
      dac->calibrate(obj);
      break;

    case circ::block_type_t::INTEG:
      integ = common::get_slice(fab,loc.loc)->integrator;
      integ->calibrate(obj);
      break;

    case circ::block_type_t::LUT:
      break;

    default:
      comm::error("calibrate: unexpected block");

    }
  }

  void set_codes(Fabric* fab,
                 uint16_t blk,
                 circ::circ_loc_idx1_t loc,
                 block_code_t& state)
  {
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice::ChipAdc * adc;
    Fabric::Chip::Tile::Slice::Dac * dac;
    Fabric::Chip::Tile::Slice::Integrator * integ;
    Fabric::Chip::Tile::Slice::LookupTable * lut;

    switch(blk)
      {
      case circ::block_type_t::FANOUT:
        fanout = common::get_fanout(fab,loc);
        fanout->update(state.fanout);
        break;
      case circ::block_type_t::TILE_ADC:
        adc = common::get_slice(fab,loc.loc)->adc;
        adc->update(state.adc);
        break;

      case circ::block_type_t::TILE_DAC:
        dac = common::get_slice(fab,loc.loc)->dac;
        dac->update(state.dac);
        break;
      case circ::block_type_t::LUT:
        lut = common::get_slice(fab,loc.loc)->lut;
        lut->update(state.lut);
        break;

      case circ::block_type_t::MULT:
        mult = common::get_mult(fab,loc);
        mult->update(state.mult);
        break;
      case circ::block_type_t::INTEG:
        integ = common::get_slice(fab,loc.loc)->integrator;
        integ->update(state.integ);
        break;
      default:
        comm::error("set_codes: unimplemented block");
      }
  }
  void get_codes(Fabric* fab,
                 uint16_t blk,
                 circ::circ_loc_idx1_t loc,
                 block_code_t& state)
  {
    uint8_t idx = 0;
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice::ChipAdc * adc;
    Fabric::Chip::Tile::Slice::Dac * dac;
    Fabric::Chip::Tile::Slice::Integrator * integ;
    Fabric::Chip::Tile::Slice::LookupTable * lut;

    switch(blk)
      {
      case circ::block_type_t::FANOUT:
        fanout = common::get_fanout(fab,loc);
        state.fanout = fanout->m_codes;
        break;
      case circ::block_type_t::MULT:
        // TODO: indicate if input or output.
        mult = common::get_mult(fab,loc);
        state.mult = mult->m_codes;
        break;
      case circ::block_type_t::TILE_ADC:
        adc = common::get_slice(fab,loc.loc)->adc;
        state.adc = adc->m_codes;
        break;
      case circ::block_type_t::LUT:
        lut = common::get_slice(fab,loc.loc)->lut;
        state.lut = lut->m_codes;
        break;
      case circ::block_type_t::TILE_DAC:
        dac = common::get_slice(fab,loc.loc)->dac;
        state.dac = dac->m_codes;
        break;
      case circ::block_type_t::INTEG:
        integ = common::get_slice(fab,loc.loc)->integrator;
        state.integ = integ->m_codes;
        break;
      default:
        comm::error("get_offset_code: unexpected block");
      }
  }
}
