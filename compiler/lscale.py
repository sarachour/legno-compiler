import hwlib.adp as adplib
import hwlib.block as blocklib
import ops.base_op as baseoplib
import ops.generic_op as genoplib
import ops.opparse as opparse
import numpy as np
import compiler.lscale_pass.lscale_solver as lscale_solver
import compiler.lscale_pass.lscale_ops as scalelib

def generate_dynamical_system_info(program,adp):
  ivals = scalelib.DynamicalSystemInfo()
  for config in adp.configs:
    for stmt in config.stmts_of_type(adplib.ConfigStmtType.PORT):
      #print(stmt)
      pass

  return ivals

'''
Factor out a constant coefficient from an expression. Return the base expression
and the constant coefficient.
'''
def get_expr_coefficient(expr):
  if expr.op == baseoplib.OpType.INTEG:
    return 1.0,expr
  elif expr.op == baseoplib.OpType.MULT:
    c1,e1 = get_expr_coefficient(expr.arg(0))
    c2,e2 = get_expr_coefficient(expr.arg(1))
    if e1 is None and e2 is None:
      return c1*c2,genoplib.Const(1.0)
    elif e1 is None:
      return c1*c2,e2
    elif e2 is None:
      return c1*c2,e1
    else:
      return c1*c2,genoplib.Mult(e1,e2)
  elif expr.op == baseoplib.OpType.ADD:
    c1,_e1 = get_expr_coefficient(expr.arg(0))
    c2,_e2 = get_expr_coefficient(expr.arg(1))
    e1 = genoplib.Const(1) if _e1 is None else _e1
    e2 = genoplib.Const(1) if _e2 is None else _e2
    if c1 == c2:
      return c1,genoplib.Add(e1,e2)
    else:
      return c1,genoplib.Add(e1,genoplib.Mult(genoplib.Const(c2/c1),e2))

  elif expr.op == baseoplib.OpType.CONST:
    return expr.value,None
  elif expr.op == baseoplib.OpType.VAR:
    return 1.0,expr
  elif expr.op == baseoplib.OpType.EMIT:
    c1,_e1 = get_expr_coefficient(expr.arg(0))
    return c1,genoplib.Emit(_e1,expr.loc)
  else:
    raise Exception("unhandled: %s" % expr)
'''
If there's any integration operation in the expression,
reshuffle terms so it is the toplevel node
'''
def canonicalize_integration_operation(expr):
  has_integ_op = any(map(lambda n: n.op == baseoplib.OpType.INTEG, expr.nodes()))
  if has_integ_op:
    if expr.op == baseoplib.OpType.MULT:
      c,e = get_expr_coefficient(expr)
      if(e.op == baseoplib.OpType.INTEG):
        return genoplib.Integ(
          genoplib.Mult(genoplib.Const(c),e.deriv),
          genoplib.Mult(genoplib.Const(c),e.init_cond),
          ":x"
        )
    elif expr.op == baseoplib.OpType.INTEG:
      return expr
    else:
      raise Exception("unhandled: %s" % expr)
  else:
    return expr

'''
try and make one expression a template for the other
if they're not compatible, return False,_,_
if they're compatible, return True,coeff,base_expr
'''
def templatize(baseline_expr,targ_expr):
    bl_coeff,bl_expr = get_expr_coefficient(baseline_expr)
    t_coeff,t_expr = get_expr_coefficient(targ_expr)
    if np.sign(bl_coeff) == np.sign(t_coeff) and \
       bl_expr == t_expr:
      return True,t_coeff/bl_coeff,bl_expr
    else:
      return False,None,None

def generate_factor_constraints(inst,rel):
  if rel.op == baseoplib.OpType.INTEG:
    c1,mderiv = generate_factor_constraints(inst,rel.deriv)
    c2,mic = generate_factor_constraints(inst,rel.init_cond)
    monomial = scalelib.SCMonomial()
    monomial.product(mderiv)
    monomial.add_term(scalelib.TimeScaleVar())
    cspeed = scalelib.SCEq(monomial,mic)
    return c1+c2+[cspeed],mic

  if rel.op == baseoplib.OpType.VAR:
    variable = scalelib.PortScaleVar(inst,rel.name)
    return [],scalelib.SCMonomial.make_var(variable)

  if rel.op == baseoplib.OpType.CONST:
    return [],scalelib.SCMonomial.make_const(rel.value)


  if rel.op == baseoplib.OpType.MULT:
    c1,op1 = generate_factor_constraints(inst,rel.arg(0))
    c2,op2 = generate_factor_constraints(inst,rel.arg(1))
    m = scalelib.SCMonomial()
    m.product(op1)
    m.product(op2)
    return c1+c2,m

  if rel.op == baseoplib.OpType.EMIT:
    c,op = generate_factor_constraints(inst,rel.arg(0))

    return c,op

  else:
    raise Exception(rel)

def templatize_and_factor_relation(hwinfo,inst,output,baseline_mode,modes):
  '''
  Create a relation with ConstVars instead of coefficients.
  Divide each mode relation by the baseline. If the shape doesn't match
  up, raise an exception
  '''
  templ = canonicalize_integration_operation(hwinfo \
                                             .get_relation(inst, \
                                                           baseline_mode, \
                                                           output))
  if templ.op == baseoplib.OpType.INTEG:
    _,bl_deriv_expr = get_expr_coefficient(templ.deriv)
    _,bl_ic_expr = get_expr_coefficient(templ.init_cond)
    deriv_coeff_var = scalelib.ConstCoeffVar(inst,output,0)
    ic_coeff_var = scalelib.ConstCoeffVar(inst,output,1)

    # produce necessary factor constraints
    cstrs,bl_deriv_monom = generate_factor_constraints(inst,bl_deriv_expr)
    for cstr in cstrs:
      yield cstr

    cstrs,bl_ic_monom = generate_factor_constraints(inst,bl_ic_expr)
    for cstr in cstrs:
      yield cstr

    deriv_monom = scalelib.SCMonomial()
    deriv_monom.add_term(deriv_coeff_var)
    deriv_monom.add_term(scalelib.TimeScaleVar())
    deriv_monom.product(bl_deriv_monom)

    ic_monom = scalelib.SCMonomial()
    ic_monom.add_term(deriv_coeff_var)
    ic_monom.product(bl_deriv_monom)

    yield scalelib.SCEq(deriv_monom,ic_monom)
    yield scalelib.SCEq(ic_monom,scalelib.PortScaleVar(inst,output))

    # derive assignments for coefficients
    valid_modes = []
    for mode in modes:
      targ= hwinfo.get_relation(inst,mode,output)
      canon= canonicalize_integration_operation(targ)
      ic_succ,ic_coeff,ic_expr = templatize(templ.init_cond,canon.init_cond)
      der_succ,der_coeff,der_expr = templatize(templ.deriv,canon.deriv)
      if ic_succ and der_succ:
        yield scalelib.SCModeImplies(scalelib.ModeVar(inst), \
                                     modes,mode,deriv_coeff_var,der_coeff)
        yield scalelib.SCModeImplies(scalelib.ModeVar(inst), \
                                     modes,mode,ic_coeff_var,ic_coeff)
        valid_modes.append(mode)

    yield scalelib.SCSubsetOfModes(scalelib.ModeVar(inst),valid_modes,modes)

  else:
    coeff_var = scalelib.ConstCoeffVar(inst,output,0)
    _,bl_expr = get_expr_coefficient(templ)

    cstrs,bl_monom = generate_factor_constraints(inst,bl_expr)
    for cstr in cstrs:
      yield cstr

    monom = scalelib.SCMonomial()
    monom.add_term(coeff_var)
    monom.product(bl_monom)
    yield scalelib.SCEq(monom,scalelib.PortScaleVar(inst,output))

    valid_modes = []
    for mode in modes:
      targ= hwinfo.get_relation(inst,mode,output)
      succ,coeff,expr = templatize(templ,targ)
      if succ:
        yield scalelib.SCModeImplies(scalelib.ModeVar(inst), \
                                     modes,mode,coeff_var,coeff)
        valid_modes.append(mode)

    yield scalelib.SCSubsetOfModes(scalelib.ModeVar(inst),valid_modes,modes)


def generate_constraint_problem(dev,program,adp):
  dsinfo = generate_dynamical_system_info(program,adp)
  hwinfo = scalelib.HardwareInfo(dev)

  for conn in adp.conns:
    yield scalelib.SCEq(scalelib.PortScaleVar(conn.source_inst,conn.source_port), \
               scalelib.PortScaleVar(conn.dest_inst, conn.dest_port))

  for config in adp.configs:
    mode_var = scalelib.ModeVar(config.inst)
    block = dev.get_block(config.inst.block)
    # identify which modes can be templatized
    for out in block.outputs:
      for cstr in templatize_and_factor_relation(hwinfo,
                                      config.inst, \
                                      out.name, \
                                      config.modes[0],
                                      block.modes):
        yield cstr

      # ensure the expression is factorable


    # any data-specific constraints
    for mode in block.modes:
      for datum in block.data:
        if datum.type == blocklib.BlockDataType.CONST:
          pass
        elif datum.type == blocklib.BlockDataType.EXPR:
          pass
        else:
          raise NotImplementedError

      # generate interval, freq limitation, and port constraints
      for port in list(block.inputs) + list(block.outputs):
        interval = port.interval[mode]
        freq_lim = port.freq_limit[mode]
        if hasattr(port,'quantize'):
          quantize = port.quantize[mode]


def scale(dev, program, adp):
  cstr_prob = []
  for stmt in generate_constraint_problem(dev,program,adp):
    cstr_prob.append(stmt)

  for adp in lscale_solver.solve(dev,adp,cstr_prob):
    yield adp

