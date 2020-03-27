#include "Circuit.h"
#include "Common.h"
#include "AnalogLib.h"
#include "Comm.h"

namespace common {


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
  Fabric::Chip::Tile::Slice* get_slice(Fabric * fab, block_loc_t& loc){
    if(loc.chip < 0 || loc.chip > 1
         || loc.tile < 0 || loc.tile > 3
         || loc.slice < 0 || loc.slice > 3)
      {
        sprintf(FMTBUF, "unknown loc %d.%d.%d", loc.chip,loc.tile,loc.slice);
        error(FMTBUF);
      }
    return &fab->chips[loc.chip].tiles[loc.tile].slices[loc.slice];
  }

  Fabric::Chip::Tile::Slice::Multiplier* get_mult(Fabric * fab,
                                                  block_loc_t& loc){
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice * slice = get_slice(fab,loc);
    switch(loc.idx){
    case 0:
      mult = &slice->muls[0];
      break;
    case 1:
      mult = &slice->muls[1];
      break;
    default:
      comm::error("unknown multiplier index (not 0 or 1).");
      break;
    }
    return mult;
  }

  Fabric::Chip::Tile::Slice::Fanout* get_fanout(Fabric * fab,
                                                block_loc_t& loc){
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice * slice = get_slice(fab,loc);
    switch(loc.idx){
    case 0:
      fanout = &slice->fans[0];
      break;
    case 1:
      fanout = &slice->fans[1];
      break;
    default:
      comm::error("unknown fanout index (not 0 or 1).");
      break;
    }
    return fanout;
  }



  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* get_input_port(Fabric * fab,
                                                                     port_loc_t loc)
  {
    Fabric::Chip::Tile::Slice * slice = get_slice(fab,loc.inst);
    switch(loc.inst.block){
    case block_type_t::TILE_DAC:
      comm::error("dac has no input port");
      break;
    case block_type_t::TILE_ADC:
      return slice->adc->in0;
      break;
    case block_type_t::MULT:
      switch(loc.port){
      case in0Id:
        return slice->muls[loc.inst.idx].in0;
        break;
      case in1Id:
        return slice->muls[loc.inst.idx].in1;
        break;
      default:
        comm::error("unknown mult input");
        break;
      }
    case block_type_t::INTEG:
      return slice->integrator->in0;
      break;
    case block_type_t::TILE_INPUT:
      return slice->tileInps[loc.inst.idx].in0;
      break;
    case block_type_t::TILE_OUTPUT:
      return slice->tileOuts[loc.inst.idx].in0;
      break;
    case block_type_t::FANOUT:
      return get_fanout(fab,loc.inst)->in0;
      break;
    case block_type_t::CHIP_OUTPUT:
      return slice->chipOutput->in0;
      break;
    case block_type_t::CHIP_INPUT:
      comm::error("no input port for chip_input");
      break;
    case block_type_t::LUT:
      comm::error("unhandled: lut");
      break;
    }
    return NULL;
  }



  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* get_output_port(Fabric * fab,
                                                                      port_loc_t loc)
  {
    Fabric::Chip::Tile::Slice * slice = get_slice(fab,loc.inst);
    switch(loc.inst.block){
    case block_type_t::TILE_DAC:
      return slice->dac->out0;
      break;
    case block_type_t::MULT:
      return slice->muls[loc.inst.idx].out0;
      break;
    case block_type_t::INTEG:
      return slice->integrator->out0;
      break;
    case block_type_t::TILE_OUTPUT:
      return slice->tileOuts[loc.inst.idx].out0;
      break;
    case block_type_t::TILE_INPUT:
      return slice->tileInps[loc.inst.idx].out0;
      break;
    case block_type_t::FANOUT:
      switch(loc.port){
      case out0Id:
        return get_fanout(fab,loc.inst)->out0;
        break;
      case out1Id:
        return get_fanout(fab,loc.inst)->out1;
        break;
      case out2Id:
        return get_fanout(fab,loc.inst)->out2;
        break;
      default:
        comm::error("unknown fanout output");
        break;
    }
    case block_type_t::CHIP_INPUT:
      return slice->chipInput->out0;
      break;
    case block_type_t::CHIP_OUTPUT:
      comm::error("no output port for chip_output");
      break;
    case block_type_t::LUT:
      comm::error("unhandled: lut");
      break;
    case block_type_t::TILE_ADC:
      comm::error("unhandled: tile_adc");
      break;

    }
    return NULL;
  }
}
