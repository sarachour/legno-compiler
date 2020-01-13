import compiler.lscale_pass.scenv as scenv
import ops.scop as scop
import compiler.lscale_pass.lscale_util as lscale_util
import compiler.lscale_pass.scenv as scenvlib
import numpy as np
from gpkit import Variable,Model

import util.config as CONFIG
import signal

'''
def gpkit_expr(variables,expr):
    if expr.op == scop.SCOpType.VAR:
        return variables[expr.name]**float(expr.exponent)

    elif expr.op == scop.SCOpType.MULT:
        e1 = gpkit_expr(variables,expr.arg(0))
        e2 = gpkit_expr(variables,expr.arg(1))
        return e1*e2

    elif expr.op == scop.SCOpType.CONST:
        return float(expr.value)

    else:
        raise Exception("unsupported <%s>" % expr)

def build_gpkit_cstrs(circ,scenv):
  failed = scenv.failed()
  if failed:
    lscale_util.log_warn("==== FAIL ====")
    for fail in scenv.failures():
      lscale_util.log_warn(fail)
    return


  variables = {}
  constraints = []
  blacklist = []
  for var in scenv.variables(in_use=True):
    gpvar = Variable(var)
    assert(not var in variables)
    variables[var] = gpvar

  for lhs,rhs,annot in scenv.eqs():
      gp_lhs = gpkit_expr(variables,lhs)
      gp_rhs = gpkit_expr(variables,rhs)
      result = (gp_lhs == gp_rhs)
      msg="%s == %s" % (gp_lhs,gp_rhs)
      if not annot in blacklist:
        constraints.append((gp_lhs == gp_rhs,msg))

  for lhs,rhs,annot in scenv.ltes():
      gp_lhs = gpkit_expr(variables,lhs)
      gp_rhs = gpkit_expr(variables,rhs)
      msg="%s <= %s" % (gp_lhs,gp_rhs)
      if not annot in blacklist:
        constraints.append((gp_lhs <= gp_rhs,msg))


  gpkit_cstrs = []
  for cstr,msg in constraints:
      if isinstance(cstr,bool) or isinstance(cstr,np.bool_):
          if not cstr:
              print("[[false]]: %s" % (msg))
              input()
              failed = True
          else:
              print("[[true]]: %s" % (msg))
      else:
          gpkit_cstrs.append(cstr)
          #print("[q] %s" % msg)

  if failed:
      print("<< failed >>")
      time.sleep(0.2)
      return

  cstrs = list(gpkit_cstrs)
  return variables,cstrs

def validate_gpkit_problem(scenv,variables,sln):
    assigns = {}
    tol = 1e-3
    for jvar,gpvar in variables.items():
        value = sln['freevariables'][gpvar]
        assert(not jvar in assigns)
        assigns[jvar] = value

    for lhs,rhs,annot in scenv.eqs():
        lhs_val = lhs.evaluate(assigns)
        rhs_val = rhs.evaluate(assigns)
        if abs(lhs_val-rhs_val) > tol:
            print("%s==%s" % (lhs,rhs))
            raise Exception("doesn't validate")


    for lhs,rhs,annot in scenv.ltes():
        lhs_val = lhs.evaluate(assigns)
        rhs_val = rhs.evaluate(assigns)
        if abs(min(0,rhs_val-lhs_val)) > tol:
            print("%s<=%s" % (lhs,rhs))
            raise Exception("doesn't validate")


def build_gpkit_problem(circ,scenv,jopt):
  variables,gpkit_cstrs = build_gpkit_cstrs(circ,scenv)
  if gpkit_cstrs is None:
    print("could not build constraints")
    input()
    return


  for obj in jopt.objective(circ,variables):
      cstrs = list(gpkit_cstrs) + list(obj.constraints())
      ofun = gpkit_expr(variables,obj.objective())
      lscale_util.log_info(ofun)
      model = Model(ofun, cstrs)
      yield variables,model,obj

def solve_gpkit_problem_cvxopt(gpmodel,timeout=10):
    def handle_timeout(signum,frame):
        raise TimeoutError("solver timed out")
    try:
        signal.signal(signal.SIGALRM, handle_timeout)
        signal.alarm(timeout)
        sln = gpmodel.solve(solver='cvxopt',verbosity=0)
        signal.alarm(0)
    except RuntimeWarning:
        signal.alarm(0)
        return None
    except TimeoutError as te:
        print("Timeout: cvxopt timed out or hung")
        signal.alarm(0)
        return None

    except ValueError as ve:
        print("ValueError: %s" % ve)
        signal.alarm(0)
        return None

    return sln


def solve_gpkit_problem_mosek(gpmodel,timeout=10):
    def handle_timeout(signum,frame):
        raise TimeoutError("solver timed out")
    try:
        signal.signal(signal.SIGALRM, handle_timeout)
        signal.alarm(timeout)
        sln = gpmodel.solve(solver=CONFIG.GPKIT_SOLVER,
                            warn_on_check=True,
                            verbosity=0)
        signal.alarm(0)
    except TimeoutError as te:
        lscale_util.log_warn("Timeout: mosek timed out or hung")
        signal.alarm(0)
        return None
    except RuntimeWarning as re:
        lscale_util.log_warn("[gpkit][ERROR] %s" % re)
        signal.alarm(0)
        return None

    if not 'freevariables' in sln:
      succ,result = sln
      lscale_util.log_warn("[gpkit][ERROR] no freevariables key in sln")
      assert(result is None)
      assert(succ == False)
      return None

    return sln


def solve_gpkit_problem(gpmodel,timeout=10):
  if CONFIG.GPKIT_SOLVER == 'cvxopt':
    return solve_gpkit_problem_cvxopt(gpmodel,timeout)
  else:
    return solve_gpkit_problem_mosek(gpmodel,timeout)

def debug_gpkit_problem(gpprob):
  jaunt_util.log_warn(">>> DEBUG <<<")
  result = gpprob.debug(solver=CONFIG.GPKIT_SOLVER)

'''
