#ifndef EXPERIMENT_H
#define EXPERIMENT_H
#include <DueTimer.h>
#include "Circuit.h"
#include "math.h"

//#define SDA_PIN SDA
#define SDA_PIN SDA1

namespace experiment {

typedef struct experiment_data {
  bool use_osc;
  bool use_analog_chip;
  float sim_time_sec;
  // input data
  int16_t * databuf;

} experiment_t;

typedef enum cmd_type {
  RESET,
  USE_ANALOG_CHIP,
  SET_SIM_TIME,
  USE_OSC,
  RUN,
} cmd_type_t;

typedef union args {
  float floats[3];
  uint32_t ints[3];
} args_t;

typedef struct cmd {
  uint16_t type;
  args_t args;
  uint8_t flag;
} cmd_t;

void setup_experiment(experiment_t * expr);
void set_dac_value(experiment_t * expr, byte dac_id,int sample,float data);
void enable_adc(experiment_t * expr, byte adc_id);
void enable_oscilloscope(experiment_t * expr);
void enable_analog_chip(experiment_t * expr);
void reset_experiment(experiment_t * expr);
void enable_dac(experiment_t * expr, byte dac_id);
short* get_adc_values(experiment_t * expr, byte adc_id, int& num_samples);
void exec_command(experiment_t * expr, Fabric * fab, cmd_t& cmd, float* inbuf);
void debug_command(experiment_t * expr, Fabric * fab, cmd_t& cmd, float* inbuf);
void print_command(cmd_t& cmd, float* inbuf);
}
#endif
