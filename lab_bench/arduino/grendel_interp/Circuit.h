#ifndef CIRCUIT_H
#define CIRCUIT_H

#define _DUE
#include "AnalogLib.h"

namespace circ {

  const uint8_t LOW_RANGE = RANGE_LOW;
  const uint8_t MED_RANGE = RANGE_MED;
  const uint8_t HI_RANGE = RANGE_HIGH;

  typedef enum block_type {
    //0
    TILE_DAC,
    // 1-4
    CHIP_INPUT,
    CHIP_OUTPUT,
    TILE_INPUT,
    TILE_OUTPUT,
    //5
    MULT,
    //6
    INTEG,
    //7
    FANOUT,
    //8-9
    LUT,
    TILE_ADC
  } block_type_t;

  // TODO interpreter for commands
  typedef enum cmd_type {
    /*use components 0-5 */
    USE_DAC,
    USE_MULT,
    USE_FANOUT,
    USE_INTEG,
    USE_LUT,
    USE_ADC,
    /*disable components 6-12 */
    DISABLE_DAC,
    DISABLE_MULT,
    DISABLE_INTEG,
    DISABLE_FANOUT,
    DISABLE_LUT,
    DISABLE_ADC,
    /*connection 12-14 */
    CONNECT,
    BREAK,
    /*debug 14-15 */
    GET_INTEG_STATUS,
    GET_ADC_STATUS,
    /*set values 16 */
    WRITE_LUT,
    /*calibration 17-18*/
    CALIBRATE,
    TUNE,
    /*state 19-20*/
    GET_STATE,
    SET_STATE,
    DEFAULTS,
    CHARACTERIZE
  } cmd_type_t;

  typedef struct circ_loc {
    uint8_t chip;
    uint8_t tile;
    uint8_t slice;
  } circ_loc_t;

  typedef struct circ_loc_idx1 {
    circ_loc_t loc;
    uint8_t idx;
  } circ_loc_idx1_t;

  typedef struct circ_loc_idx2 {
    circ_loc_idx1_t idxloc;
    uint8_t idx2;
  } circ_loc_idx2_t;

  typedef struct use_integ {
    circ_loc_t loc;
    uint8_t inv;
    uint8_t in_range;
    uint8_t out_range;
    uint8_t debug;
    float value;
  } cmd_use_integ_t;

  typedef enum code_type {
    CODE_END,
    CODE_PMOS,
    CODE_PMOS2,
    CODE_NMOS,
    CODE_OFFSET,
    CODE_GAIN_OFFSET,
    CODE_I2V_OFFSET,
    CODE_COMP_LOWER,
    CODE_COMP_LOWER_FS,
    CODE_COMP_UPPER,
    CODE_COMP_UPPER_FS
  } code_type_t;


  typedef struct use_dac {
    circ_loc_t loc;
    uint8_t source;
    uint8_t inv;
    uint8_t out_range;
    float value;
  } cmd_use_dac_t;

  typedef struct use_mult {
    circ_loc_idx1_t loc;
    uint8_t use_coeff;
    uint8_t inv;
    uint8_t in0_range;
    uint8_t in1_range;
    uint8_t out_range;
    float coeff;
  } cmd_use_mult_t;

  typedef struct use_lut {
    circ_loc_t loc;
    uint8_t source;
  } cmd_use_lut_t;


  typedef struct write_lut {
    circ_loc_t loc;
    uint8_t offset;
    uint8_t n;
  } cmd_write_lut_t;

  typedef struct use_adc {
    circ_loc_t loc;
    uint8_t in_range;
  } cmd_use_adc_t;

  typedef struct use_fanout {
    circ_loc_idx1_t loc;
    uint8_t inv[3];
    uint8_t in_range;
    uint8_t third;
  } cmd_use_fanout_t;

  typedef struct connection {
    uint16_t src_blk;
    circ_loc_idx2_t src_loc;
    uint16_t dst_blk;
    circ_loc_idx2_t dst_loc;
  } cmd_connection_t;

  typedef struct {
    uint8_t calib_obj;
    uint16_t blk;
    circ_loc_idx1_t loc;
  } cmd_calib_t;

  typedef struct {
    uint8_t mode;
    uint16_t blk;
    circ_loc_idx1_t loc;
    float in0;
    float in1;
  } cmd_prof_t;

  typedef struct {
    uint16_t blk;
    circ_loc_idx1_t loc;
    uint8_t data[64];
  } cmd_state_t;

  typedef union cmddata {
    cmd_use_fanout_t fanout;
    cmd_use_integ_t integ;
    cmd_use_mult_t mult;
    cmd_use_dac_t dac;
    cmd_use_lut_t lut;
    cmd_write_lut_t write_lut;
    cmd_use_adc_t adc;
    cmd_connection_t conn;
    circ_loc_t circ_loc;
    circ_loc_idx1_t circ_loc_idx1;
    cmd_state_t state;
    cmd_calib_t calib;
    cmd_prof_t prof;
  } cmd_data_t;

  typedef struct cmd {
    uint16_t type;
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
#endif CIRCUIT_H
