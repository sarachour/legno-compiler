#ifndef CIRCUIT_H
#define CIRCUIT_H

#define _DUE
#include "AnalogLib.h"

namespace circ {

  const uint8_t LOW_RANGE = RANGE_LOW;
  const uint8_t MED_RANGE = RANGE_MED;
  const uint8_t HI_RANGE = RANGE_HIGH;


  // TODO interpreter for commands
  typedef enum cmd_type {
    NULLCMD,
    DISABLE,
    CONNECT,
    BREAK,
    GET_BLOCK_STATUS,
    WRITE_LUT,
    CALIBRATE,
    GET_STATE,
    SET_STATE,
    DEFAULTS,
    PROFILE
  } cmd_type_t;


  typedef struct write_lut {
    block_loc_t inst;
    uint8_t offset;
    uint8_t n;
  } cmd_write_lut_t;


  typedef struct connection {
    port_loc_t src;
    port_loc_t dst;
  } cmd_connect_t;

  typedef struct disable {
    block_loc_t inst;
  } cmd_disable_t;


  typedef struct {
    calib_objective_t calib_obj;
    block_loc_t inst;
  } cmd_calib_t;

  typedef struct {
    profile_spec_t spec;
  } cmd_profile_t;

  typedef struct {
    block_loc_t inst;
  } cmd_get_block_status_t;


  typedef struct {
    block_loc_t inst;
  } cmd_get_state_t;

  typedef struct {
    block_loc_t inst;
    block_code_t state;
  } cmd_set_state_t;

  typedef union cmddata {
    cmd_write_lut_t write_lut;
    cmd_connect_t conn;
    cmd_disable_t disable;
    cmd_get_block_status_t get_status;
    cmd_get_state_t get_state;
    cmd_set_state_t set_state;
    cmd_calib_t calib;
    cmd_profile_t prof;
  } cmd_data_t;

  typedef struct cmd {
    uint8_t type;
    cmd_data_t data;
  } cmd_t;

  //Fabric* setup_board();
  //void init_calibrations();
  void timeout(Fabric * fab, unsigned int timeout);
  void print_command(cmd_t& cmd);
  void print_state(block_type_t blk, block_code_t state);
  void exec_command(Fabric * fab, cmd_t& cmd, float* inbuf);
  void debug_command(Fabric * fab, cmd_t& cmd, float* inbuf);

}
#endif
