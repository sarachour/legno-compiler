import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.physdb as physdb
import hwlib.hcdc.llenums as llenums

import phys_model.phys_util as phys_util
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


def fit_model(variables,expr,data):

  #print("*********START OF FIT_MODEL*********")
  inputs = data['inputs']
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

def fit_delta_model_to_data(phys,relation,data):
  try:
    result = fit_model(phys.delta_model.spec.params,relation,data)
  except TypeError as e:
    print("insufficient data: %d points" % (len(data['meas_mean'])))
    return False


  for par,val in result['params'].items():
    if par in relation.vars():
      phys.delta_model.bind(par,val)

  return True

def compute_delta_model_error(phys,data):
  inputs = data['inputs']
  meas_output = data['meas_mean']
  sumsq = phys.delta_model.error(inputs,meas_output)
  phys.delta_model.model_error = sumsq
  phys.update()

def fit_delta_model_integrator(phys):
  relation = phys.delta_model.spec.relation

  ic_dataset = phys.dataset.get_data( \
                                   llenums.ProfileStatus.SUCCESS, \
                                   llenums.ProfileOpType.INTEG_INITIAL_COND)
  if len(ic_dataset['meas_mean']) == 0:
    return

  result = fit_delta_model_to_data(phys,relation.init_cond, ic_dataset)

  deriv_dataset = phys.dataset.get_data( \
                                         llenums.ProfileStatus.SUCCESS, \
                                         llenums.ProfileOpType.INTEG_DERIVATIVE_GAIN)

  if len(deriv_dataset['meas_mean']) == 0:
    return

  if not fit_delta_model_to_data(phys,relation.deriv,deriv_dataset):
    return

  sumsq = phys.delta_model.error(ic_dataset['inputs'], \
                                 ic_dataset['meas_mean'], \
                                 init_cond=True)

  phys.delta_model.model_error = sumsq
  phys.update()



def fit_delta_model(phys):
  delta_spec = phys.delta_model.spec
  assert(isinstance(delta_spec,blocklib.DeltaSpec))
  phys.delta_model.clear()
  if delta_spec.relation.op == oplib.OpType.INTEG:
    fit_delta_model_integrator(phys)
  else:
    dataset = phys.dataset.get_data( \
                                     llenums.ProfileStatus.SUCCESS, \
                                     llenums.ProfileOpType.INPUT_OUTPUT)
    if not fit_delta_model_to_data(phys, delta_spec.relation, dataset):
      return

    compute_delta_model_error(phys,dataset)
