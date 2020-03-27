#ifndef COMMON_H
#define COMMON_H


namespace common {

  int get_block_status(Fabric* fab, block_loc_t blk);
  void disable_block(Fabric* fab, block_loc_t blk);

  Fabric::Chip::Tile::Slice* get_slice(Fabric * fab,
                                       block_loc_t& loc);
  Fabric::Chip::Tile::Slice::Multiplier* get_mult(Fabric * fab,
                                                  block_loc_t& loc);
  Fabric::Chip::Tile::Slice::Fanout* get_fanout(Fabric * fab,
                                                block_loc_t& loc);
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* get_input_port(Fabric * fab,
                                                                     port_loc_t& loc);
  Fabric::Chip::Tile::Slice::FunctionUnit::Interface* get_output_port(Fabric * fab,
                                                                      port_loc_t& loc);

}
#endif
