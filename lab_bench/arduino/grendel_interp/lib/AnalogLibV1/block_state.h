#ifndef FU_BLOCKSTATE
#define FU_BLOCKSTATE

#include <stdint.h>
/*Valid options for functional unit interface.*/
// the order actually really matters here
typedef enum {
	in0Id,
	in1Id,
	out0Id,
	out1Id,
	out2Id
} ifc;

/*signal range configuration*/

typedef enum {
	mulMid = 0, /* -2 to 2  uA*/
	mulLo = 1,  /*-.2 to .2 uA*/
	mulHi = 2,  /*-20 to 20 uA*/
} mulRange;

typedef enum {
  RANGE_HIGH,
  RANGE_MED,
  RANGE_LOW,
  RANGE_UNKNOWN
} range_t;

typedef enum {
  DSRC_MEM,
  DSRC_EXTERN,
  DSRC_LUT0,
  DSRC_LUT1
} dac_source_t;

typedef enum {
  LSRC_ADC0,
  LSRC_ADC1,
  LSRC_EXTERN,
  LSRC_CONTROLLER,
} lut_source_t;

typedef enum {
  CALIB_MINIMIZE_ERROR,
  CALIB_MAXIMIZE_DELTA_FIT,
  CALIB_FAST
} calib_objective_t;

typedef struct {
  bool test_en;
  bool test_adc;
  bool test_i2v;
  bool test_rs;
  bool test_rsinc;
  bool enable;
  uint8_t pmos;
  uint8_t nmos;
  uint8_t pmos2;
  uint8_t i2v_cal;
  uint8_t upper_fs;
  uint8_t upper;
  uint8_t lower_fs;
  uint8_t lower;
  range_t range;
} adc_state_t;

typedef struct {
  bool vga;
  bool enable;
  range_t range[3];
  uint8_t pmos;
  uint8_t nmos;
  uint8_t port_cal[3];
  uint8_t gain_cal;
  uint8_t gain_code;
} mult_state_t;


typedef struct {
  bool enable;
  bool inv;
  range_t range;
  dac_source_t source;
  uint8_t pmos;
  uint8_t nmos;
  uint8_t gain_cal;
  uint8_t const_code;
} dac_state_t;

typedef struct {
  bool cal_enable[3];
  bool inv;
  bool enable;
  bool exception;
  range_t range[3];
  uint8_t pmos;
  uint8_t nmos;
  uint8_t gain_cal;
  uint8_t ic_code;
  uint8_t port_cal[3];
} integ_state_t;


typedef struct {
  uint8_t pmos;
  uint8_t nmos;
  range_t range;
  uint8_t port_cal[5];
  bool inv[5];
  bool enable;
  bool third;
} fanout_state_t;

typedef struct {
  lut_source_t source;
} lut_state_t;

typedef union {
  lut_state_t lut;
  fanout_state_t fanout;
  dac_state_t dac;
  adc_state_t adc;
  mult_state_t mult;
  integ_state_t integ;
} block_state_t;



typedef enum block_type {
  //0
  NO_BLOCK,
  //1
  TILE_DAC,
  // 2-5
  CHIP_INPUT,
  CHIP_OUTPUT,
  TILE_INPUT,
  TILE_OUTPUT,
  //6
  MULT,
  //7
  INTEG,
  //8
  FANOUT,
  //9-10
  LUT,
  TILE_ADC
} block_type_t;


#define port_type_t ifc

typedef struct block_loc {
  block_type_t block;
  uint8_t chip;
  uint8_t tile;
  uint8_t slice;
  uint8_t idx;
} block_loc_t;

typedef struct port_loc {
  block_loc_t inst;
  ifc port;
} port_loc_t;

typedef enum {
  INPUT_OUTPUT,
  INTEG_INITIAL_COND,
  INTEG_DERIVATIVE_STABLE,
  INTEG_DERIVATIVE_BIAS,
  INTEG_DERIVATIVE_GAIN
} profile_type_t;


typedef struct {
  block_loc_t inst;
  float inputs[2];
  profile_type_t type;
  port_type_t output;
  block_state_t state;
} profile_spec_t;

typedef enum {
  SUCCESS,
  FAILED_TO_CALIBRATE
} profile_status_t;

typedef struct {
  profile_spec_t spec;
  profile_status_t status;
  float mean;
  float stdev;
} profile_t;

/*
typedef union {
  profile_t result;
  unsigned char charbuf[sizeof(profile_t)];
} serializable_profile_t;
*/


ifc port_type_to_ifc(port_type_t port);
const char * lut_source_to_string(lut_source_t src);
const char * dac_source_to_string(dac_source_t src);
const char * block_type_to_string(block_type_t type);
const char * port_type_to_string(port_type_t type);
int sprintf_block_inst(block_loc_t& inst, char * buf);
int sprintf_block_port(port_loc_t& loc,char * buf);
int sprintf_block_state(block_type_t blk, block_state_t state, char * BUF);
const char * profile_status_to_string(profile_status_t status);
void sprintf_profile_spec(profile_spec_t& result, char * buf);
void sprintf_profile(profile_t& result, char * buf);

#endif
