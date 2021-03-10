import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.llenums as llenums
from hwlib.hcdc.llcmd_calibrate import calibrate
from hwlib.hcdc.llcmd_profile import profile
import hwlib.hcdc.hcdcv2 as hcdclib
import itertools
import ops.op as oplib

from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum
import numpy as np


def calibrate(dev,runtime,block,inst,cfg):
  assert(cfg.inst.block == block.name)
  assert(cfg.inst.loc == inst)
  new_adp= adplib.ADP()
  new_adp.add_instance(block,inst)
  config = new_adp.configs.get(block.name, \
                               inst)
  config.set_config(cfg)
  all_codes = calibrate(runtime,block,inst, \
                              new_adp, \
                              method=llenums.CalibrateObjective.MAXIMIZE_FIT)
  print(all_codes)



def profile_hidden_state(runtime,dev,planner,hidden,adp=None,quiet=False):
  # make new config for profiling operation
  if adp is None:
     new_adp= adplib.ADP()
     new_adp.add_instance(planner.block,planner.loc) 
  else:
     new_adp = adp.copy(dev)
     
  config = new_adp.configs.get(planner.block.name, \
                                  planner.loc)
  config.set_config(planner.config)

  # set hidden state
  for state_var,value in hidden.items():
    stmt = config.get(state_var)
    assert(isinstance(stmt,adplib.StateConfig))
    stmt.value = value


  planner.new_dynamic()
  output = planner.output
  method = planner.method
  dynamic = planner.next_dynamic()
  while not dynamic is None:
    input_vals = {}
    for name,value in dynamic.items():
      if planner.block.data.has(name):
        assert(isinstance(config[name],  \
                          adplib.ConstDataConfig))
        config[name].value = value
      else:
        st = planner.block.inputs[name]
        input_vals[st.ll_identifier] = value
    
    if not quiet:
       print("-> input %s" % str(dynamic))

    profile(runtime, \
            dev, \
            planner.block, \
            planner.loc, \
            new_adp, \
            output.ll_identifier, \
            method=method, \
            inputs=input_vals, \
            quiet=quiet)

    dynamic = planner.next_dynamic()

def profile_all_hidden_states(runtime,dev,planner,adp=None,quiet=False):
  planner.new_hidden()
  hidden_state = planner.next_hidden()
  while not hidden_state is None:
    print(hidden_state)
    profile_hidden_state(runtime,dev,planner,hidden_state,adp=adp,quiet=quiet)
    hidden_state = planner.next_hidden()
