import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.physdb as physdb
import hwlib.hcdc.llenums as llenums

import phys_model.phys_util as phys_util
import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
import itertools

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

def fit_model(variables,expr,data):
  inputs = data['inputs']
  meas_output = data['meas_mean']
  n_inputs = len(inputs.keys())
  #if phys.model.complete:
  #  return False

  repl = {}
  dataset = [None]*n_inputs
  for idx,bound_var in enumerate(inputs.keys()):
    assert(len(inputs[bound_var]) == len(meas_output))
    dataset[idx] = inputs[bound_var]
    repl[bound_var] = genoplib.Var("x[%d]" % idx)

  conc_expr = expr.substitute(repl)
  _,pyexpr = lambdoplib.to_python(conc_expr)
  fields = {
    'free_vars':",".join(variables),
    'free_var_array':",".join(map(lambda p: '"%s"' % p, variables)),
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
  return {
    'params': dict(zip(parameters,parameter_values)),
    'param_error': parameter_stdevs
  }

def fit_delta_model(phys,data):
  model = phys.model.delta_model
  result = fit_model(model.params,model.relation,data)
  phys.model.clear()
  for par,val in result['params'].items():
    phys.model.bind(par,val)

  inputs = data['inputs']
  meas_output = data['meas_mean']
  sumsq = phys.model.error(inputs,meas_output)
  phys.model.cost = sumsq
  phys.update()

def analyze_physical_output(phys_output,operation=llenums.ProfileOpType.INPUT_OUTPUT):
  dataset = phys_output.dataset
  fit_delta_model(phys_output, \
                  phys_output.dataset.get_data( \
                                  llenums.ProfileStatus.SUCCESS, \
                                                operation))
