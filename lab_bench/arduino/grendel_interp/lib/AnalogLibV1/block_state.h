#ifndef FU_BLOCKSTATE
#define FU_BLOCKSTATE

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
} adc_code_t;

typedef struct {
  bool vga;
  bool enable;
  range_t range[3];
  uint8_t pmos;
  uint8_t nmos;
  uint8_t port_cal[3];
  uint8_t gain_cal;
  uint8_t gain_code;
} mult_code_t;


typedef struct {
  bool enable;
  bool inv;
  range_t range;
  dac_source_t source;
  uint8_t pmos;
  uint8_t nmos;
  uint8_t gain_cal;
  uint8_t const_code;
} dac_code_t;

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
} integ_code_t;


typedef struct {
  uint8_t pmos;
  uint8_t nmos;
  range_t range;
  uint8_t port_cal[5];
  bool inv[5];
  bool enable;
  bool third;
} fanout_code_t;

typedef struct {
  lut_source_t source;
} lut_code_t;

typedef union {
  lut_code_t lut;
  fanout_code_t fanout;
  dac_code_t dac;
  adc_code_t adc;
  mult_code_t mult;
  integ_code_t integ;
  unsigned char charbuf[24];
} block_code_t;

#endif
