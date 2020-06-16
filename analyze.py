import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.physdb as physdb
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib

import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
import itertools

def get_subarray(arr,inds):
  return list(map(lambda i: arr[i], inds))

PROG = '''
from scipy.optimize import curve_fit
import numpy as np

def func(x,{free_vars}):
  return {expr}


xdata = {x_dataset}


ydata = {y_dataset}


popt,pcov = curve_fit(func,xdata,ydata)
lbls = [{free_var_array}]
assigns = dict(zip(lbls,popt))
perr = np.sqrt(np.diag(pcov))
'''

def fit_delta_model(phys,inputs,meas_output):
  n_inputs = len(inputs.keys())
  if phys.model.complete:
    return

  model = phys.model.delta_model
  # for building expression
  repl = {}
  dataset = [None]*n_inputs
  for idx,bound_var in enumerate(inputs.keys()):
    assert(len(inputs[bound_var]) == len(meas_output))
    dataset[idx] = inputs[bound_var]
    repl[bound_var] = genoplib.Var("x[%d]" % idx)

  expr = model.relation.substitute(repl)
  _,pyexpr = lambdoplib.to_python(expr)
  fields = {
    'free_vars':",".join(model.params),
    'free_var_array':",".join(map(lambda p: '"%s"' % p, model.params)),
    'x_dataset': str(dataset),
    'y_dataset': str(meas_output),
    'expr':pyexpr
  }
  snippet = PROG.format(**fields)
  loc = {}
  exec(snippet,globals(),loc)
  parameters = loc['lbls']
  parameter_values = loc['popt']
  parameter_stdevs = loc['perr']
  for idx,par in enumerate(parameters):
    val = parameter_values[idx]
    phys.model.bind(par,val)

  sumsq = phys.model.error(inputs,meas_output)
  phys.model.cost = sumsq
  print("cost: %s" % phys.model.cost)
  phys.update()

def analyze_physical_output(phys_output):
  def valid_data_point(dataset,method,idx):
    return dataset.meas_status[idx] == llenums.ProfileStatus.SUCCESS \
      and dataset.meas_method[idx] == method

  delta_model = phys_output.model.delta_model
  dataset = phys_output.dataset
  indices = list(filter(lambda idx: valid_data_point(dataset, \
                                                  llenums.ProfileOpType.INPUT_OUTPUT, \
                                                  idx), range(0,dataset.size)))

  meas = get_subarray(dataset.meas_mean,indices)
  meas_stdev = get_subarray(dataset.meas_stdev,indices)
  ref = get_subarray(dataset.output, indices)
  variables = {}
  for data_field,values in dataset.data.items():
    variables[data_field] = values

  for input_field,values in dataset.inputs.items():
    variables[input_field] = values

  params = fit_delta_model(phys_output,variables,meas)

dev = hcdclib.get_device()
#block = dev.get_block('fanout')
block = dev.get_block('mult')
inst = devlib.Location([0,3,2,0])
cfg = adplib.BlockConfig.make(block,inst)
#cfg.modes = [['+','+','-','m']]
cfg.modes = [block.modes.get(['x','m','m'])]
# program hidden codes
out = block.outputs["z"]


db = physdb.PhysicalDatabase('board6')
for blk in physdb.get_all_calibrated_blocks(db,dev,block,inst,cfg):
  analyze_physical_output(blk)

print("===== BEST ====")
for blk in physdb.get_best_calibrated_block(db,dev,block,inst,cfg):
  print(blk.hidden_cfg)
