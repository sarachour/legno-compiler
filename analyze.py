import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.physdb as physdb
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib

import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib

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

def fit_delta_model(model,inputs,meas_output):
  n_inputs = len(inputs.keys())

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
    stdev = parameter_stdevs[idx]
    print("%s = %s stdev:%s" % (par,val,stdev))

  raise NotImplementedError

def analyze(db,block,inst,out,cfg):
  def valid_data_point(dataset,method,idx):
    return dataset.meas_status[idx] == llenums.ProfileStatus.SUCCESS \
      and dataset.meas_method[idx] == method

  phys_block = llcmd.phys_block(db,block,inst,out,cfg)
  dataset = phys_block.dataset
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

  # test to see that delta model is fully specified
  delta_model = phys_block.output.deltas[cfg.mode]
  free_variables = delta_model.params
  bound_variables = list(variables.keys())
  for v in delta_model.relation.vars():
    if not v in free_variables and  \
       not v in bound_variables:
      raise Exception("no data for bound variable: %s" % v)

  params = fit_delta_model(delta_model,variables,meas)

dev = hcdclib.get_device()
#block = dev.get_block('fanout')
block = dev.get_block('mult')
inst = devlib.Location([0,3,2,0])
cfg = adplib.BlockConfig.make(block,inst)
#cfg.modes = [['+','+','-','m']]
cfg.modes = [block.modes.get(['x','h','m'])]
# program hidden codes
cfg.get('pmos').value = 0
cfg.get('nmos').value = 0
cfg.get('gain_cal').value = 0
cfg.get('bias_in0').value = 0
cfg.get('bias_in1').value = 0
cfg.get('bias_out').value = 0

out = block.outputs["z"]

db = physdb.PhysicalDatabase('board6')
analyze(db,block,inst,out,cfg)

