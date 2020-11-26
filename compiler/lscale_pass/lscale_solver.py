import ops.smtop as smtlib
import compiler.lscale_pass.lscale_ops as scalelib
import hwlib.block as blocklib
import hwlib.adp as adplib
import math

class SymbolTable:

  def __init__(self,env):
    self.symbols = {}
    self.smtenv = env

  def declare(self,v):
    if not str(v) in self.symbols:
      self.symbols[str(v)] = v
      if isinstance(v,scalelib.ModeVar):
        self.smtenv.decl(str(v),smtlib.SMTEnv.Type.INT)
      elif isinstance(v,scalelib.PortScaleVar) or \
         isinstance(v,scalelib.TimeScaleVar) or\
         isinstance(v,scalelib.ConstCoeffVar) or \
         isinstance(v,scalelib.PropertyVar) or \
         isinstance(v,scalelib.InjectVar) or \
         isinstance(v,scalelib.QualityVar):
        self.smtenv.decl(str(v),smtlib.SMTEnv.Type.REAL)
      else:
        raise Exception("unknown var: %s" % v)

  def get(self,v):
    return self.symbols[v]

def take_log(value):
  return math.log(value)

def undo_log(value):
  return math.exp(value)

def monomial_to_z3_expr(expr):
  if isinstance(expr,scalelib.SCVar):
    return smtlib.SMTVar(str(expr))

  result = smtlib.SMTConst(take_log(expr.coeff))
  for term,expo in expr.terms:
    term_z3 = smtlib.SMTMult(smtlib.SMTConst(expo), \
                      smtlib.SMTVar(str(term)))
    result = smtlib.SMTAdd(result,term_z3)

  return result

def var_value_to_logval(var,value):
  if isinstance(var,scalelib.ConstCoeffVar):
    return take_log(value)
  if isinstance(var,scalelib.PropertyVar):
    return take_log(value)
  else:
    raise Exception("unknown: %s" % var)

def scale_cstr_to_z3_cstr(smtenv,cstr):
  if isinstance(cstr,scalelib.SCEq):
    z3_lhs = monomial_to_z3_expr(cstr.lhs)
    z3_rhs = monomial_to_z3_expr(cstr.rhs)
    smtenv.eq(z3_lhs,z3_rhs)

  elif isinstance(cstr,scalelib.SCLTE):
    z3_lhs = monomial_to_z3_expr(cstr.lhs)
    z3_rhs = monomial_to_z3_expr(cstr.rhs)
    smtenv.lte(z3_lhs,z3_rhs)


  elif isinstance(cstr,scalelib.SCIntervalCover):
    if not cstr.valid():
      print("invalid: %s" % cstr)
      smtenv.fail("invalid: %s" % cstr)
      return

    (triv_lb,triv_ub) = cstr.trivial()
    if not triv_lb:
      lhs = cstr.submonom.lower.copy()
      lhs.coeff = lhs.coeff*abs(cstr.subinterval.lower)
      rhs = cstr.monom.lower.copy()
      rhs.coeff = rhs.coeff*abs(cstr.interval.lower)

      z3_lhs = monomial_to_z3_expr(lhs)
      z3_rhs = monomial_to_z3_expr(rhs)
      smtenv.lte(z3_lhs,z3_rhs)

    if not triv_ub:
      lhs = cstr.submonom.upper.copy()
      lhs.coeff = lhs.coeff*abs(cstr.subinterval.upper)
      rhs = cstr.monom.upper.copy()
      rhs.coeff = rhs.coeff*abs(cstr.interval.upper)

      z3_lhs = monomial_to_z3_expr(lhs)
      z3_rhs = monomial_to_z3_expr(rhs)
      smtenv.lte(z3_lhs,z3_rhs)


  elif isinstance(cstr,scalelib.SCModeImplies):
    modes = list(cstr.mode_var.modes)
    mode_index = modes.index(cstr.mode)
    logval = var_value_to_logval(cstr.dep_var,cstr.value)
    mode_eq = smtlib.SMTEq(smtlib.SMTVar(str(cstr.mode_var)), \
                           smtlib.SMTConst(mode_index))
    val_eq = smtlib.SMTEq(smtlib.SMTVar(str(cstr.dep_var)), \
                          smtlib.SMTConst(logval))

    implies = smtlib.SMTImplies(mode_eq,val_eq)
    smtenv.cstr(implies)

  elif isinstance(cstr,scalelib.SCSubsetOfModes):
    modes = list(cstr.mode_var.modes)
    clauses = []
    for m in cstr.valid_modes:
      if not m in modes:
        raise Exception("mode <%s> not in %s" % (str(m),str(cstr.modes)))
      index = modes.index(m)
      clauses.append(smtlib.SMTEq(smtlib.SMTVar(str(cstr.mode_var)), \
                                  smtlib.SMTConst(index)))

    assert(len(clauses) > 0)
    cstr = clauses[0]
    for mode_cstr in clauses[1:]:
      cstr = smtlib.SMTOr(cstr,mode_cstr)

    smtenv.cstr(cstr)

  else:
    raise Exception("not implemented: %s <%s>" % (cstr,cstr.__class__.__name__))

def scale_objective_fun_to_z3_objective_fun(objfun):
  return monomial_to_z3_expr(objfun)

class LScaleSolutionGenerator:

  def __init__(self,dev,adp,symtbl,smtenv,opt=None):
    assert(isinstance(symtbl,SymbolTable))
    assert(isinstance(smtenv,smtlib.SMTEnv))
    ctx,opt = smtenv.to_z3(optimize=opt)
    self.smtenv = smtenv
    self.symtbl = symtbl
    self.z3ctx = ctx
    self.z3opt = opt
    self.adp = adp
    self.dev = dev

  def solutions(self):
    adp = self.get_solution()
    while not adp is None:
      yield adp
      adp = self.get_solution()

  def get_solution(self):
    if self.z3opt is None:
      result = self.z3ctx.solve()
    else:
      self.z3ctx.set_objective(self.z3opt)
      result = self.z3ctx.optimize()
    if result is None:
      print("no solution..")
      return None
    else:
      print("found solution!")

    symtbl = self.symtbl
    adp = self.adp.copy(self.dev)
    quality = None
    model_to_negate = {}
    for var_name,value in result.items():
      var = symtbl.get(var_name)
      if isinstance(var,scalelib.ModeVar):
        blkcfg = adp.configs.get(var.inst.block,var.inst.loc)
        blk = self.dev.get_block(var.inst.block)
        mode = blk.modes[int(value)]
        assert(isinstance(mode,blocklib.BlockMode))
        blkcfg.modes = [mode]
        if len(blk.modes) > 1:
          model_to_negate[var_name] = value

      elif isinstance(var,scalelib.PortScaleVar):
        if not value is None:
          blkcfg = adp.configs.get(var.inst.block,var.inst.loc)
          blkcfg[var.port].scf = undo_log(value)

      elif isinstance(var,scalelib.TimeScaleVar):
        adp.tau = undo_log(value)

      elif isinstance(var,scalelib.InjectVar):
        val = undo_log(value)
        blkcfg = adp.configs.get(var.inst.block,var.inst.loc)
        inj_key = var.field if var.arg is None else var.arg
        blkcfg[var.field].injs[inj_key] = val

      elif isinstance(var,scalelib.QualityVar):
        quality = scalelib.QualityMeasure(var.name)
        val = undo_log(value)
        if quality == scalelib.QualityMeasure.AQM:
          adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_AQM, val)
        elif quality == scalelib.QualityMeasure.DQM:
          adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_DQM, val)
        else:
          raise Exception("unknown quality measure: %s" % quality)

      elif isinstance(var,scalelib.ConstCoeffVar) or \
           isinstance(var,scalelib.PropertyVar):
        continue
      else:
        raise Exception("unimpl: %s" % var)

    self.z3ctx.negate_model(model_to_negate)
    return adp



def solve(dev,adp,cstrs,objective_fun):
  smtenv = smtlib.SMTEnv()
  symtbl = SymbolTable(smtenv)
  for cstr in cstrs:
    for v in cstr.vars():
      symtbl.declare(v)

  for cstr in cstrs:
    scale_cstr_to_z3_cstr(smtenv,cstr)

  z3_obj_fun = scale_objective_fun_to_z3_objective_fun(objective_fun)
  generator = LScaleSolutionGenerator(dev,adp,symtbl,smtenv, \
                                      opt=z3_obj_fun)
  for scaled_adp in generator.solutions():
    yield scaled_adp


