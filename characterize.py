import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib
import itertools

from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum
import math
import numpy as np

def select_from_array(arr,n):
  space = math.ceil(len(arr)/n)
  subarr = arr[0:len(arr):space]
  return subarr

def select_from_interval(ival,n):
  return list(np.linspace(ival.lower,ival.upper,n))

def select_from_quantized_interval(ival,quant,n):
  values = quant.get_values(ival)
  return select_from_array(values,n)

def profile(runtime,blk,inst,hidden,templ_config,m=5):
  new_adp= adplib.ADP()
  new_adp.add_instance(blk,inst)
  config = new_adp.configs.get(block.name,inst)
  config.set_config(templ_config)

  # set hidden state
  for state_var,value in hidden.items():
    stmt = config.get(state_var.name)
    assert(isinstance(stmt,adplib.StateConfig))
    stmt.value = value

  # determine which variables impact output
  variables = []
  outputs = {}
  for out in blk.outputs:
    outputs[out.name] = out.ll_identifier
    variables += list(out.relation[config.mode].vars())

  # build up dynamically changing codes
  dynamic = {}
  for inp in filter(lambda inp: inp.name in variables, blk.inputs):
    dynamic[inp] = select_from_interval(inp.interval[config.mode],m)

  for data in filter(lambda dat: dat.name in variables, blk.data):
    dynamic[data] = select_from_quantized_interval(data.interval[config.mode], \
                                                  data.quantize[config.mode], \
                                                  m)

  # sweep over input space
  dynamic_fields = list(dynamic.keys())
  dynamic_values = list(map(lambda k :dynamic[k], dynamic_fields))
  for comb in itertools.product(*dynamic_values):
    assigns = dict(zip(dynamic_fields,comb))
    input_vals = {}
    for st,value in assigns.items():
      if isinstance(st,blocklib.BlockData):
        assert(isinstance(config[st.name],  \
                          adplib.ConstDataConfig))
        config[st.name].value = value
      else:
        input_vals[st.ll_identifier] = value

    for output,output_ident in outputs.items():
      print(input_vals)
      llcmd.profile(runtime,blk,inst,new_adp,output_ident, \
                    method=llenums.ProfileOpType.INPUT_OUTPUT, \
                    inputs=input_vals)

def characterize(blk,inst,cfg,n=5,m=10):
  hidden = {}
  for state in filter(lambda st: isinstance(st.impl, \
                                            blocklib.BCCalibImpl), \
                      blk.state):
    hidden[state] = select_from_array(state.values,n)


  runtime = GrendelRunner()
  runtime.initialize()

  hidden_fields = list(hidden.keys())
  hidden_values = list(map(lambda k :hidden[k], hidden_fields))

  for comb in itertools.product(*hidden_values):
    hidden_assigns = dict(zip(hidden_fields,comb))
    profile(runtime,blk,inst,hidden_assigns,cfg,m=m)


dev = hcdclib.get_device()
#block = dev.get_block('fanout')
block = dev.get_block('mult')
inst = devlib.Location([0,3,2,0])
cfg = adplib.BlockConfig.make(block,inst)
#cfg.modes = [['+','+','-','m']]
cfg.modes = [block.modes.get(['x','h','m'])]
characterize(block,inst,cfg)

