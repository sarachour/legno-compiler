import ops.op as op
import numpy as np
import scipy.integrate
import math
import json

def find_stvars(var,expr,stvars,ics):
  def visit(e):
    return find_stvars(var,e,stvars,ics)

  if expr.op == op.OpType.INTEG:
    handle = expr.handle
    key = "%s%s" % (var,handle)
    ics[key] = expr.init_cond.value
    stvars[key] = visit(expr.deriv)
    return op.Var(key)

  elif expr.op == op.OpType.ADD:
    return op.Add(visit(expr.arg1),visit(expr.arg2))
  elif expr.op == op.OpType.MULT:
    return op.Mult(visit(expr.arg1),visit(expr.arg2))
  elif expr.op == op.OpType.VAR or \
       expr.op == op.OpType.EXTVAR or \
       expr.op == op.OpType.CONST:
    return expr
  elif expr.op == op.OpType.EMIT:
    return op.Emit(visit(expr.arg(0)))

def compute_varmap(y,t,fnvars,stvars,extfns,fns):
  vmap = dict(zip(stvars,y))
  for var,(expr,_) in extfns.items():
    args = {'t':t, 'math':math}
    vmap[var] = eval(expr,args)

  for var in fnvars:
    vmap[var] = fns[var].compute(vmap)

  return vmap

def compute_deriv(y,t,fnvars,stvars,extfns,fns,stfns):
  vmap = compute_varmap(y,t,fnvars,stvars,extfns,fns)
  dmap = {}
  for var,expr in stfns.items():
    dmap[var] = expr.compute(vmap)

  for i,var in enumerate(stvars):
    y[i] = dmap[var]
  print(y)
  return y

def build_dataset(ys,ts,fnvars,stvars,extfns,fns,stfns):
  data = {'t':[]}
  for y,t in zip(ys,ts):
    print(y,t)
    data['t'].append(t)
    vmap = compute_varmap(y,t,fnvars,stvars,extfns,fns)
    for var,value in vmap.items():
      if not var in data:
        data[var] = []
      data[var].append(value)

  return data

def compute_func_vars(fnmap):
  depmap = {}
  variables = []
  for var,expr in fnmap.items():
    depmap[var] = list(filter(lambda v : v in fnmap,
                            expr.vars()))

  while len(variables) < len(fnmap.keys()):
    nvars = len(variables)
    for var,deps in depmap.items():
      if all(map(lambda v: v in variables, deps)) and \
         not var in variables:
        variables.append(var)

    if nvars == len(variables):
      raise Exception("[error] circular depedency")

  return variables

def execute(path_handler,prog,menv,n=10000):
  stfns = {}
  ics = {}
  fns = {}
  extfns = {}
  for var in prog.variables():
    expr = prog.binding(var)
    if expr is None:
      extfns[var] = menv.input(var)
    else:
      new_expr = find_stvars(var,expr,stfns,ics)
      fns[var] = new_expr

  fnvars = compute_func_vars(fns)
  stvars = list(stfns.keys())
  y0 = list(map(lambda v: ics[v], stvars))
  t = np.linspace(0,menv.sim_time,n)
  ys = scipy.integrate.odeint(compute_deriv,y0,t,\
                             args=(fnvars, \
                                   stvars,\
                                   extfns,\
                                   fns,\
                                   stfns))

  dataset = build_dataset(ys,t,fnvars,stvars, \
                          extfns,fns,stfns)

  relevent_dataset = {}
  relevent_dataset['time'] = dataset['t']
  for var in prog.variables():
    relevent_dataset[var] = dataset[var]

  filename = path_handler\
             .reference_waveform_file(prog.name,
                                      menv.name)
  with open(filename,'w') as fh:
    fh.write(json.dumps(relevent_dataset))

