import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib
import itertools
import ops.op as oplib

import phys_model.phys_util as phys_util
from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum
import numpy as np


def profile_calibrated_block(dev,runtime,planner,hidden):
  # make new config for profiling operation
  new_adp= adplib.ADP()
  new_adp.add_instance(planner.block,planner.loc)
  config = new_adp.configs.get(planner.block.name, \
                               planner.loc)
  config.set_config(planner.config)

  # set hidden state
  for state_var,value in hidden.items():
    stmt = config.get(state_var.name)
    assert(isinstance(stmt,adplib.StateConfig))
    stmt.value = value


  planner.new_dynamic()
  dynamic = planner.next_dynamic()
  while not dynamic is None:
    input_vals = {}
    for st,value in dynamic.items():
      if isinstance(st,blocklib.BlockData):
        assert(isinstance(config[st.name],  \
                          adplib.ConstDataConfig))
        config[st.name].value = value
      else:
        input_vals[st.ll_identifier] = value

    for output in planner.block.outputs:
      if phys_util.is_integration_op(output.relation[config.mode]):
        methods = [llenums.ProfileOpType.INTEG_INITIAL_COND, \
                   llenums.ProfileOpType.INTEG_DERIVATIVE_STABLE, \
                   llenums.ProfileOpType.INTEG_DERIVATIVE_BIAS, \
                   llenums.ProfileOpType.INTEG_DERIVATIVE_GAIN]
        input()
        raise NotImplementedError
      else:
        methods = [llenums.ProfileOpType.INPUT_OUTPUT]

      for method in methods:
        llcmd.profile(runtime, \
                      planner.block, \
                      planner.loc, \
                      new_adp, \
                      output.ll_identifier, \
                      method=method, \
                      inputs=input_vals)

    dynamic = planner.next_dynamic()

def profile_uncalibrated_block(dev,planner):
  runtime = GrendelRunner()
  runtime.initialize()

  hidden_state = planner.next_hidden()
  while not hidden_state is None:
    profile_calibrated_block(dev,runtime,planner,hidden_state)
    hidden_state = planner.next_hidden()
