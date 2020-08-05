import ops.smtop as smtlib
import compiler.lscale_pass.scale_ops as scalelib
import math

class SymbolTable:

  def __init__(self,env):
    self.symbols = {}
    self.smtenv = env

  def declare(self,v):
    if not str(v) in self.symbols:
      if isinstance(v,scalelib.ModeVar):
        self.smtenv.decl(str(v),smtlib.SMTEnv.Type.INT)
      elif isinstance(v,scalelib.PortScaleVar) or \
         isinstance(v,scalelib.TimeScaleVar) or\
         isinstance(v,scalelib.ConstCoeffVar):
        self.smtenv.decl(str(v),smtlib.SMTEnv.Type.REAL)
      else:
        raise Exception("unknown var: %s" % v)

def take_log(value):
  return math.log(value)

def monomial_to_z3_expr(expr):
  if isinstance(expr,scalelib.SCVar):
    return smtlib.SMTVar(str(expr))

  result = smtlib.SMTConst(take_log(expr.coeff))
  for term,expo in expr.terms:
    term_z3 = smtlib.SMTMult(smtlib.SMTConst(expo), \
                      smtlib.SMTVar(str(term)))
    result = smtlib.SMTAdd(result,term_z3)

  return result

def scale_cstr_to_z3_cstr(smtenv,cstr):
  if isinstance(cstr,scalelib.SCEq):
    z3_lhs = monomial_to_z3_expr(cstr.lhs)
    z3_rhs = monomial_to_z3_expr(cstr.rhs)
    smtenv.eq(z3_lhs,z3_rhs)

  elif isinstance(cstr,scalelib.SCModeImplies):
    mode_index = cstr.modes.index(cstr.mode)
    mode_eq = smtlib.SMTEq(smtlib.SMTVar(cstr.mode_var), \
                           smtlib.SMTConst(mode_index))
    val_eq = smtlib.SMTEq(smtlib.SMTVar(cstr.dep_var), \
                          smtlib.SMTConst(cstr.value))
    print(mode_eq,val_eq)
    print("mode: %d" % mode_index)
    raise Exception("implies not implemented: %s" % cstr)

  else:
    raise Exception("not implemented: %s <%s>" % (cstr,cstr.__class__.__name__))

def solve(cstrs):
  smtenv = smtlib.SMTEnv()
  symtbl = SymbolTable(smtenv)
  for cstr in cstrs:
    for v in cstr.vars():
      symtbl.declare(v)

  for cstr in cstrs:
    scale_cstr_to_z3_cstr(smtenv,cstr)
  raise NotImplementedError

