#ifndef COMMON_H
#define COMMON_H


namespace common {

  Fabric::Chip::Tile::Slice* get_slice(Fabric * fab,
                                       circ::circ_loc_t& loc);
  Fabric::Chip::Tile::Slice::Multiplier* get_mult(Fabric * fab,
                                                  circ::circ_loc_idx1_t& loc);
  Fabric::Chip::Tile::Slice::Fanout* get_fanout(Fabric * fab,
                                                circ::circ_loc_idx1_t& loc);
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* get_input_port(Fabric * fab,
                                                                     uint16_t btype,
                                                                     circ::circ_loc_idx2_t& loc);
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* get_output_port(Fabric * fab,
                                                                   uint16_t btype,
                                                                   circ::circ_loc_idx2_t& loc);

}
#endif
