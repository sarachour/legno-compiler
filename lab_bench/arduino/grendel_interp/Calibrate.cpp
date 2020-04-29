#include "AnalogLib.h"
#include "Circuit.h"
#include "Common.h"
#include "Comm.h"
#include "fu.h"
#include "profile.h"
#include "block_state.h"

namespace calibrate {
  calib_objective_t get_objective_max_delta_fit(uint16_t blk){
    switch(blk){
    case block_type_t::FANOUT:
      return CALIB_FAST;
      break;
    case block_type_t::MULT:
      return CALIB_MAXIMIZE_DELTA_FIT;
      break;
    default:
      return CALIB_MINIMIZE_ERROR;
    }
  }
  calib_objective_t get_objective_min_error(uint16_t blk){
    switch(blk){
    case block_type_t::TILE_ADC:
    case block_type_t::FANOUT:
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
    return macro_obj;
  }


  profile_t measure(Fabric* fab,
                    profile_spec_t& spec)
  {
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice::ChipAdc * adc;
    Fabric::Chip::Tile::Slice::Dac * dac;
    Fabric::Chip::Tile::Slice::Integrator * integ;
    //Fabric::Chip::Tile::Slice::LookupTable * lut;
    switch(spec.inst.block){
    case block_type_t::FANOUT:
      fanout = common::get_fanout(fab,spec.inst);
      return fanout->measure(spec);
      break;

    case block_type_t::MULT:
      // TODO: indicate if input or output.
      mult = common::get_mult(fab,spec.inst);
      return mult->measure(spec);
      break;

    case block_type_t::TILE_ADC:
      adc = common::get_slice(fab,spec.inst)->adc;
      return adc->measure(spec);
      break;

    case block_type_t::TILE_DAC:
      dac = common::get_slice(fab,spec.inst)->dac;
      return dac->measure(spec);
      break;

    case block_type_t::INTEG:
      integ = common::get_slice(fab,spec.inst)->integrator;
      return integ->measure(spec);
      break;

    case block_type_t::LUT:
      break;
    default:
      comm::error("get_offset_code: unexpected block");
    }
    profile_t dummy_result;
    return dummy_result;
  }

  void calibrate(Fabric* fab,
                 block_loc_t loc,
                 calib_objective_t macro_obj)
  {
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice::ChipAdc * adc;
    Fabric::Chip::Tile::Slice::Dac * dac;
    Fabric::Chip::Tile::Slice::Integrator * integ;
    calib_objective_t obj = get_objective(loc.block,macro_obj);
    switch(loc.block){
    case block_type_t::FANOUT:
      fanout = common::get_fanout(fab,loc);
      fanout->calibrate(obj);
      break;

    case block_type_t::MULT:
      // TODO: indicate if input or output.
      mult = common::get_mult(fab,loc);
      mult->calibrate(obj);
      break;

    case block_type_t::TILE_ADC:
      adc = common::get_slice(fab,loc)->adc;
      adc->calibrate(obj);
      break;

    case block_type_t::TILE_DAC:
      dac = common::get_slice(fab,loc)->dac;
      dac->calibrate(obj);
      break;

    case block_type_t::INTEG:
      integ = common::get_slice(fab,loc)->integrator;
      integ->calibrate(obj);
      break;

    case block_type_t::LUT:
      break;

    default:
      comm::error("calibrate: unexpected block");

    }
  }

  void set_codes(Fabric* fab,
                 block_loc_t loc,
                 block_state_t& state)
  {
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice::ChipAdc * adc;
    Fabric::Chip::Tile::Slice::Dac * dac;
    Fabric::Chip::Tile::Slice::Integrator * integ;
    Fabric::Chip::Tile::Slice::LookupTable * lut;

    switch(loc.block)
      {
      case block_type_t::FANOUT:
        fanout = common::get_fanout(fab,loc);
        fanout->update(state.fanout);
        break;
      case block_type_t::TILE_ADC:
        adc = common::get_slice(fab,loc)->adc;
        adc->update(state.adc);
        break;

      case block_type_t::TILE_DAC:
        dac = common::get_slice(fab,loc)->dac;
        dac->update(state.dac);
        break;
      case block_type_t::LUT:
        lut = common::get_slice(fab,loc)->lut;
        lut->update(state.lut);
        break;

      case block_type_t::MULT:
        mult = common::get_mult(fab,loc);
        mult->update(state.mult);
        break;
      case block_type_t::INTEG:
        integ = common::get_slice(fab,loc)->integrator;
        integ->update(state.integ);
        break;
      default:
        comm::error("set_codes: unimplemented block");
      }
  }
  void get_codes(Fabric* fab,
                 block_loc_t loc,
                 block_state_t& state)
  {
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice::ChipAdc * adc;
    Fabric::Chip::Tile::Slice::Dac * dac;
    Fabric::Chip::Tile::Slice::Integrator * integ;
    Fabric::Chip::Tile::Slice::LookupTable * lut;

    switch(loc.block)
      {
      case block_type_t::FANOUT:
        fanout = common::get_fanout(fab,loc);
        state.fanout = fanout->m_state;
        break;
      case block_type_t::MULT:
        // TODO: indicate if input or output.
        mult = common::get_mult(fab,loc);
        state.mult = mult->m_state;
        break;
      case block_type_t::TILE_ADC:
        adc = common::get_slice(fab,loc)->adc;
        state.adc = adc->m_state;
        break;
      case block_type_t::LUT:
        lut = common::get_slice(fab,loc)->lut;
        state.lut = lut->m_state;
        break;
      case block_type_t::TILE_DAC:
        dac = common::get_slice(fab,loc)->dac;
        state.dac = dac->m_state;
        break;
      case block_type_t::INTEG:
        integ = common::get_slice(fab,loc)->integrator;
        state.integ = integ->m_state;
        break;
      default:
        comm::error("get_offset_code: unexpected block");
      }
  }
}
