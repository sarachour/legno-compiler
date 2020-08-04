import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.physdb as physdb
import hwlib.hcdc.llenums as llenums

import phys_model.phys_util as phys_util
import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
import itertools
import math
import numpy as np
import scipy

def _prepare_minimize_model(variables,expr,params,bounds={}):
  n_inputs = len(variables)
  #if phys.model.complete:
  #  return False

  repl = {}
  dataset = [None]*n_inputs
  for idx,bound_var in enumerate(variables):
    repl[bound_var] = genoplib.Var("x[%d]" % idx)

  for par,value in params.items():
    repl[par] = genoplib.Const(value)

  bounds_arr = [(None,None)]*n_inputs
  for var,(lower,upper) in bounds.items():
    idx = variables.index(var)
    bounds_arr[idx] = (lower,upper)

  conc_expr = expr.substitute(repl)
  _,pyexpr = lambdoplib.to_python(conc_expr)
  return {
    'expr':pyexpr,
    'bounds':bounds_arr,
    'variable_array':variables
  }

GLOBAL_MIN_PROG = '''
from scipy import optimize
import numpy as np

def func(x):
  return {expr}


x0={x0}
bnds={bounds}
lbls={variable_array}
res = optimize.dual_annealing(func,bounds=bnds)
assigns = dict(zip(lbls,res.x))
'''

def global_minimize_model(variables,expr,params,bounds={}):
  fields = _prepare_minimize_model(variables,expr,params,bounds)
  fields["x0"] = list(map(lambda v: 1, variables))
  print(scipy.__version__)
  snippet = GLOBAL_MIN_PROG.format(**fields) \
                    .replace('math.','np.')
  loc = {}
  exec(snippet,globals(),loc)
  return {
    'values': loc['assigns'],
    'success': loc['res'].success,
    'objective_val': loc['res'].fun
  }



LOCAL_MIN_PROG = '''
from scipy.optimize import minimize
import numpy as np

def func(x):
  return {expr}


x0={x0}
bnds={bounds}
lbls={variable_array}
res = minimize(func,x0,bounds=bnds)
assigns = dict(zip(lbls,res.x))
'''


def local_minimize_model(variables,expr,params,bounds={}):
  fields = _prepare_minimize_model(variables,expr,params,bounds)
  fields["x0"] = list(map(lambda v: 1, variables))
  snippet = LOCAL_MIN_PROG.format(**fields) \
                    .replace('math.','np.')
  loc = {}
  exec(snippet,globals(),loc)
  return {
    'values': loc['assigns'],
    'success': loc['res'].success,
    'objective_val': loc['res'].fun
  }


def minimize_model(variables,expr,params,bounds={}):
  return local_minimize_model(variables,expr,params,bounds)

FIT_PROG = '''
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
  snippet = FIT_PROG.format(**fields) \
                    .replace('math.','np.')

  loc = {}
  if len(data['meas_mean']) == 0:
    print("DATASET: %s" % data)
    raise Exception("fit_model: cannot fit empty dataset")

  exec(snippet,globals(),loc)
  parameters = loc['lbls']
  parameter_values = loc['popt']
  parameter_stdevs = loc['perr']
  return {
    'params': dict(zip(parameters,parameter_values)),
    'param_error': parameter_stdevs
  }

def predict_output(variable_assigns,expr,data):
  inputs = data['inputs']
  meas_output = data['meas_mean']
  npts = len(meas_output)
  pred = []
  for idx in range(0,npts):
    assigns = dict(map(lambda inp: (inp,inputs[inp][idx]), \
                       inputs.keys()))
    for param,val in variable_assigns.items():
      assigns[param] = val
    value = expr.compute(assigns)
    pred.append(value)

  return pred

def fit_delta_model(phys,data):
  spec = phys.delta_model.spec
  result = fit_model(spec.params,spec.relation,data)
  phys.delta_model.clear()
  for par,val in result['params'].items():
    phys.delta_model.bind(par,val)

  inputs = data['inputs']
  meas_output = data['meas_mean']
  sumsq = phys.delta_model.error(inputs,meas_output)
  phys.delta_model.cost = sumsq
  print(result)
  print("sumsq error: %s" % phys.delta_model.cost)
  phys.update()

def analyze_physical_output(phys_output,operation=llenums.ProfileOpType.INPUT_OUTPUT):
  dataset = phys_output.dataset
  fit_delta_model(phys_output, \
                  phys_output.dataset.get_data( \
                                                llenums.ProfileStatus.SUCCESS, \
                                                operation))
