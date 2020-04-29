#include "Experiment.h"
#include "Comm.h"
#include "Circuit.h"
#include "assert.h"

experiment::experiment_t this_experiment;
Fabric * this_fabric;

typedef enum cmd_type {
  CIRC_CMD,
  EXPERIMENT_CMD,
  FLUSH_CMD
} cmd_type_t;


typedef union cmd_data {
  experiment::cmd_t exp_cmd;
  circ::cmd_t circ_cmd;
  char flush_cmd;
} cmd_data_t;

typedef struct cmd_{
  uint8_t test;
  uint8_t type;
  cmd_data_t data;
} cmd_t;


void setup() {
  this_fabric = new Fabric();
  Serial.begin(115200);
  Serial.flush();
  experiment::setup_experiment(&this_experiment);
}


void loop() {
  if(comm::read_mode()){
    cmd_t cmd;
    int nbytes = comm::read_bytes((byte *) &cmd,sizeof(cmd_t));
    float * inbuf = NULL;
    bool debug = cmd.test == 0 ? false : true;
    comm::process_command();

    switch(cmd.type){
      case cmd_type_t::CIRC_CMD:
        assert(this_fabric != NULL);
        inbuf = (float*) comm::get_data_ptr(nbytes);
        sprintf(FMTBUF, "inbuf-offset-by: %d", nbytes);
        print_log(FMTBUF);
        circ::print_command(cmd.data.circ_cmd);
        circ::exec_command(this_fabric,cmd.data.circ_cmd,inbuf);
        break;
      case cmd_type_t::EXPERIMENT_CMD:
        inbuf = (float*) comm::get_data_ptr(nbytes);
        if(!debug){
          experiment::print_command(cmd.data.exp_cmd,inbuf);
          experiment::exec_command(&this_experiment,this_fabric,cmd.data.exp_cmd,inbuf);
        }
        else{
          experiment::print_command(cmd.data.exp_cmd,inbuf);
          experiment::debug_command(&this_experiment,this_fabric,cmd.data.exp_cmd,inbuf);
        }
        // in the event the fabric has not been initialized, initialize it
        break;
      case cmd_type_t::FLUSH_CMD:
        comm::response("flushed",0);
        break;
      default:
        sprintf(FMTBUF,"unknown command: %d", cmd.type);
        comm::error(FMTBUF);
        break;
    }
    comm::reset();
  }
  else{
    comm::listen();
  }
}

