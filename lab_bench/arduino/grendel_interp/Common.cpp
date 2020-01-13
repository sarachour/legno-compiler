#include "Circuit.h"
#include "Common.h"
#include "AnalogLib.h"
#include "Comm.h"

namespace common {

  Fabric::Chip::Tile::Slice* get_slice(Fabric * fab, circ::circ_loc_t& loc){
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
                                                  circ::circ_loc_idx1_t& loc){
    Fabric::Chip::Tile::Slice::Multiplier * mult;
    Fabric::Chip::Tile::Slice * slice = get_slice(fab,loc.loc);
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
                                                circ::circ_loc_idx1_t& loc){
    Fabric::Chip::Tile::Slice::Fanout * fanout;
    Fabric::Chip::Tile::Slice * slice = get_slice(fab,loc.loc);
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
                                                                     uint16_t btype,
                                                                     circ::circ_loc_idx2_t& loc)
  {
    switch(btype){
    case circ::block_type_t::TILE_DAC:
      comm::error("dac has no input port");
      break;
    case circ::block_type_t::TILE_ADC:
      return get_slice(fab,loc.idxloc.loc)->adc->in0;
      break;
    case circ::block_type_t::MULT:
      switch(loc.idx2){
      case 0:
        return get_mult(fab,loc.idxloc)->in0;
           break;
      case 1:
        return get_mult(fab,loc.idxloc)->in1;
        break;
      default:
        comm::error("unknown mult input");
        break;
      }
    case circ::block_type_t::INTEG:
      return get_slice(fab,loc.idxloc.loc)->integrator->in0;
      break;
    case circ::block_type_t::TILE_INPUT:
      return get_slice(fab,loc.idxloc.loc)
        ->tileInps[loc.idx2].in0;
      break;
    case circ::block_type_t::TILE_OUTPUT:
      return get_slice(fab,loc.idxloc.loc)
        ->tileOuts[loc.idx2].in0;
      break;
    case circ::block_type_t::FANOUT:
      return get_fanout(fab,loc.idxloc)->in0;
      break;
    case circ::block_type_t::CHIP_OUTPUT:
      return get_slice(fab,loc.idxloc.loc)->chipOutput->in0;
      break;
    case circ::block_type_t::CHIP_INPUT:
      comm::error("no input port for chip_input");
      break;
    case circ::block_type_t::LUT:
      comm::error("unhandled: lut");
      break;
    }
  }



  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* get_output_port(Fabric * fab,
                                                                      uint16_t btype,
                                                                      circ::circ_loc_idx2_t& loc)
  {
    switch(btype){
    case circ::block_type_t::TILE_DAC:
      return get_slice(fab,loc.idxloc.loc)->dac->out0;
      break;
    case circ::block_type_t::MULT:
      return get_mult(fab,loc.idxloc)->out0;
      break;
    case circ::block_type_t::INTEG:
      return get_slice(fab,loc.idxloc.loc)->integrator->in0;
      break;
    case circ::block_type_t::TILE_OUTPUT:
      return get_slice(fab,loc.idxloc.loc)
        ->tileOuts[loc.idx2].out0;
      break;
    case circ::block_type_t::TILE_INPUT:
      return get_slice(fab,loc.idxloc.loc)
        ->tileInps[loc.idx2].out0;
      break;
    case circ::block_type_t::FANOUT:
      switch(loc.idx2){
      case 0:
        return get_fanout(fab,loc.idxloc)->out0;
        break;
      case 1:
        return get_fanout(fab,loc.idxloc)->out1;
        break;
      case 2:
        return get_fanout(fab,loc.idxloc)->out2;
        break;
      default:
        comm::error("unknown fanout output");
        break;
    }
    case circ::block_type_t::CHIP_INPUT:
      return get_slice(fab,loc.idxloc.loc)->chipInput->out0;
      break;
    case circ::block_type_t::CHIP_OUTPUT:
      comm::error("no output port for chip_output");
      break;
    case circ::block_type_t::LUT:
    comm::error("unhandled: lut");
    break;
    }
  }
}
