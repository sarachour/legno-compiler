import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llenums as llenums

import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
import ops.op as oplib
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
    if not var in variables:
       continue
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
#print("xdata:",xdata)

ydata = {y_dataset}
#print("ydata:",ydata)

#print("func:",func)


popt,pcov = curve_fit(func,xdata,ydata)
#print("popt:",popt)
#print("pcov:",pcov)
lbls = [{free_var_array}]
assigns = dict(zip(lbls,popt))
perr = np.sqrt(np.diag(pcov))
'''


def fit_model(all_vars,expr,data):

  #print("*********START OF FIT_MODEL*********")
  inputs = {}
  for varname,datum in data['inputs'].items():
    if varname in expr.vars():
      inputs[varname] = datum

  variables = []
  for varname in all_vars:
    if varname in expr.vars():
      variables.append(varname)

  if len(variables) == 0:
    return

  #print("inputs:", inputs)
  meas_output = data['meas_mean']
  #print("meas_output:", meas_output)
  n_inputs = len(inputs.keys())

  #if phys.model.complete:
  #  return False
  repl = {}
  dataset = [None]*n_inputs
  for idx,bound_var in enumerate(inputs.keys()):
    assert(len(inputs[bound_var]) == len(meas_output))
    dataset[idx] = inputs[bound_var]
    #print("dataset[idx] is:", dataset[idx])
    repl[bound_var] = genoplib.Var("x[%d]" % idx)
    #print("repl[bound_var]: ",repl[bound_var])

  conc_expr = expr.substitute(repl)
  #print("conc_expr", conc_expr)
  _,pyexpr = lambdoplib.to_python(conc_expr)
  #print("variables:",variables)
  fields = {
    'free_vars':",".join(variables),
    'free_var_array':",".join(map(lambda p: '"%s"' % p, variables)),
    'x_dataset': str(dataset),
    'y_dataset': str(meas_output),
    'expr':pyexpr
  }
  #print("fields:",fields)
  snippet = FIT_PROG.format(**fields) \
                    .replace('math.','np.')

  loc = {}
  if len(data['meas_mean']) == 0:
    raise Exception("fit_model: cannot fit empty dataset")

  exec(snippet,globals(),loc)
  parameters = loc['lbls']
  #print("parameters:",parameters)
  parameter_values = loc['popt']
  #print("parameter_values:",parameter_values)
  parameter_stdevs = loc['perr']
  #print("parameter_stdevs:",parameter_stdevs)
  #print("*********END OF FIT_MODEL*********")
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

def fit_delta_model_to_data(delta_model,relation,data):
  dataset = {}
  dataset['inputs'] = {}
  for k,v in data.inputs.items():
    dataset['inputs'][k] = v
  for k,v in data.data.items():
    dataset['inputs'][k] = v
  dataset['meas_mean'] = data.meas_mean
  

  try:
    result = fit_model(delta_model.spec.params, \
                       relation,dataset)
  except Exception as e:
    print("insufficient data: %d points" % (len(data)))
    print(e)
    return False

  if result is None:
    return False

  for par,val in result['params'].items():
    if par in relation.vars():
      delta_model.bind(par,val)

  return True
