#ifndef COMMON_H
#define COMMON_H


namespace common {

  Fabric::Chip::Tile::Slice* get_slice(Fabric * fab,
                                       circ::block_loc_t& loc);
  Fabric::Chip::Tile::Slice::Multiplier* get_mult(Fabric * fab,
                                                  circ::block_loc_t& loc);
  Fabric::Chip::Tile::Slice::Fanout* get_fanout(Fabric * fab,
                                                circ::block_loc_t& loc);
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* get_input_port(Fabric * fab,
                                                                     circ::port_loc_t& loc);
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* get_output_port(Fabric * fab,
                                                                   circ::port_loc_t& loc);

}
#endif
