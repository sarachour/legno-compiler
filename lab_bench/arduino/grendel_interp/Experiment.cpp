#include "math.h"
#include "Experiment.h"
#include "Circuit.h"
#include "Comm.h"
#include <assert.h>

namespace experiment {

volatile int SDA_VAL = LOW;

inline void set_SDA(int SDA_VAL){
  digitalWrite(SDA_PIN,SDA_VAL);
}


void setup_experiment(experiment_t* expr) {
  pinMode(SDA_PIN, OUTPUT);
  // put your setup code here, to run once:
  analogWriteResolution(12);  // set the analog output resolution to 12 bit (4096 levels)
}



void reset_experiment(experiment_t * expr){
  expr->use_analog_chip = false;
  expr->use_osc = false;
  expr->sim_time_sec = 0.0;
}


  void run_experiment(experiment_t * expr, Fabric * fab){
    // commit the configuration once.
    if(expr->use_analog_chip){
      // this actually calls start and stop.
      fab->cfgCommit();
    }
    // compute the sim time used for the delay
    float sim_time_sec = expr->sim_time_sec;
    // compute the timeout to set of the analog timer
    // if we're conducting a short simulation ,use delayus
    set_SDA(LOW);
    delayMicroseconds(2);
    if(expr->sim_time_sec < 0.1 && expr->use_analog_chip){
      unsigned int sleep_time_us = (unsigned int) (sim_time_sec*1e6);
      //set a timeout within the chip
      set_SDA(HIGH);
      fab->execStart();
      delayMicroseconds(sleep_time_us);
      fab->execStop();
    }
    // if we're conducting a longer simulation
    else if(expr->sim_time_sec >= 0.1 && expr->use_analog_chip){
      unsigned long sleep_time_ms = (unsigned long) (sim_time_sec*1e3);
      //set a timeout within the chip, if the timeout fits in uint max
      set_SDA(HIGH);
      fab->execStart();
      delay(sleep_time_ms);
      fab->execStop();
    }
    else if(expr->sim_time_sec < 0.1 && not expr->use_analog_chip){
      unsigned int sleep_time_us = (unsigned int) (sim_time_sec*1e6);
      set_SDA(HIGH);
      delayMicroseconds(sleep_time_us);
    }
    else if(expr->sim_time_sec >= 0.1 && not expr->use_analog_chip){
      unsigned long sleep_time_ms = (unsigned long) (sim_time_sec*1e3);
      set_SDA(HIGH);
      delay(sleep_time_ms);
  }
    else{
      comm::error("unrecognized case");
    }
    set_SDA(LOW);
  }


  void exec_command(experiment_t* expr, Fabric* fab, cmd_t& cmd, float * inbuf){
    switch(cmd.type){
    case cmd_type_t::RESET:
      reset_experiment(expr);
      comm::response("resetted",0);
      break;
    case cmd_type_t::RUN:
      run_experiment(expr,fab);
      comm::response("ran",0);
      break;
    case cmd_type_t::USE_ANALOG_CHIP:
      expr->use_analog_chip = true;
      comm::response("use_analog_chip=true",0);
      break;
    case cmd_type_t::USE_OSC:
      expr->use_osc = true;
      comm::response("enable_trigger=true",0);
      break;
    case cmd_type_t::SET_SIM_TIME:
      expr->sim_time_sec = cmd.args.floats[0];
      comm::response("set_sim_time",0);
      break;
    }
  }


}


