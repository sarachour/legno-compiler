import pulp
import numpy as np
import ops.smtop as smtop
import compiler.lscale_pass.lscale_util as lscale_util
import compiler.lscale_pass.scenv as scenvlib
import ops.scop as scop
import math

'''
class LinProb:

  def __init__(self):
    self._vars = {}

  def decl(self,varname):
    if not varname in self._vars:
      var = pulp.LpVariable(varname)
      self._vars[varname] = var

  def get_linvar(self,varname):
    if not varname in self._vars:
      raise Exception("not in dict[%s]" % varname)

    return self._vars[varname]

  def linvars(self):
    return self._vars.items()

def lin_expr(linenv,expr):
  def recurse(e):
    return lin_expr(linenv,e)

  if expr.op == scop.SCOpType.VAR:
    var = linenv.get_linvar(expr.name)
    return float(expr.exponent)*var

  if expr.op == scop.SCOpType.MULT:
    e1 = recurse(expr.arg(0))
    e2 = recurse(expr.arg(1))
    return e1+e2

  elif expr.op == scop.SCOpType.ADD:
    raise Exception("unsupported <%s>" % expr)

  elif expr.op == scop.SCOpType.CONST:
    return math.log(float(expr.value))

  else:
    raise Exception("unsupported <%s>" % expr)


def build_linear_problem(circ,scenv,scopt):
  failed = scenv.failed()
  if failed:
    lscale_util.log_warn("==== FAIL ====")
    for fail in scenv.failures():
      lscale_util.log_warn(fail)
    return

  lp = LinProb()
  for var in scenv.variables():
    tag = scenv.get_tag(var)
    assert(not (tag == scenvlib.LScaleVarType.MODE_VAR))
    lp.decl(var)

  constraints = []
  for lhs,rhs,annot in scenv.eqs():
    e1 = lin_expr(lp,lhs)
    e2 = lin_expr(lp,rhs)
    constraints.append((e1 == e2))

  for lhs,rhs,annot in scenv.ltes():
    e1 = lin_expr(lp,lhs)
    e2 = lin_expr(lp,rhs)
    constraints.append((e1 <= e2))

  for obj in scopt.objective(circ,scenv):
    lp.prob = pulp.LpProblem("scale", pulp.LpMinimize)
    for cstr in constraints:
      lp.prob += cstr;

    lp.prob += lin_expr(lp,obj.objective())
    yield lp,obj

def solve_linear_problem(lp):
    result = lp.prob.solve(pulp.solvers.PULP_CBC_CMD(fracGap = 1e-10))
    if not result:
      print("<<no solution>>")
      return None

    values = {}
    for varname,lpvar in lp.linvars():
      logValue = lpvar.varValue
      if logValue is None:
        continue

      value = math.exp(logValue)
      values[varname] = value

    raise Exception("this does not agree with gpkit")
    return values


'''
