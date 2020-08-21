import hwlib.adp as adplib
import hwlib.block as blocklib
import ops.base_op as baseoplib
import ops.generic_op as genoplib
import ops.opparse as opparse
import numpy as np
import compiler.lscale_pass.lscale_solver as lscale_solver
import compiler.lscale_pass.lscale_ops as scalelib
import ops.interval as ivallib

def _get_intervals(dev,dsinfo,cfg):
  blk = dev.get_block(cfg.inst.block)
  bl_mode = list(cfg.modes)[0]
  intervals = {}

  for port in blk.inputs.field_names() + blk.outputs.field_names():
    if dsinfo.has_interval(cfg.inst,port):
      intervals[port] = dsinfo.get_interval(cfg.inst,port)

  for datum in cfg.stmts_of_type(adplib.ConfigStmtType.CONSTANT):
    intervals[datum.name] = dsinfo.get_interval(cfg.inst,datum.name)

  return intervals

def _generate_dsinfo_backprop(dev,dsinfo,adp):
  count = 0
  for conn in adp.conns:
    if len(list(filter(lambda c: c.same_dest(conn), adp.conns))) > 1:
        continue

    if not dsinfo.has_interval(conn.source_inst,conn.source_port):
      if dsinfo.has_interval(conn.dest_inst, \
                             conn.dest_port):
          source_ival = dsinfo.get_interval(conn.dest_inst, \
                                            conn.dest_port)
          dsinfo.set_interval(conn.source_inst,conn.source_port,source_ival)
          count += 1

  for cfg in adp.configs:
    intervals = _get_intervals(dev,dsinfo,cfg)
    blk = dev.get_block(cfg.inst.block)
    bl_mode = list(cfg.modes)[0]

    for out in blk.outputs:
      if out.name in intervals:
        rel = out.relation[bl_mode]
        try:
          inp_intervals = ivallib.backpropagate_intervals(rel,intervals[out.name], \
                                                          intervals)
        except ivallib.UnknownIntervalError as e:
          continue

        for port_name,ival in inp_intervals.items():
          dsinfo.set_interval(cfg.inst,port_name,ival)
          count += 1

  return count

def _generate_dsinfo_recurse(dev,dsinfo,adp):
  count = 0
  for conn in adp.conns:
    if not dsinfo.has_interval(conn.dest_inst,conn.dest_port):
      ival = ivallib.Interval.type_infer(0,0)
      for src_conn in \
          list(filter(lambda c: c.same_dest(conn), adp.conns)):
        if dsinfo.has_interval(src_conn.source_inst, \
                               src_conn.source_port):
          src_ival = dsinfo.get_interval(src_conn.source_inst, \
                                         src_conn.source_port)
          ival = ival.add(src_ival)
        else:
          ival = None
          break

      if not ival is None:
        dsinfo.set_interval(conn.dest_inst,conn.dest_port,ival)
        count += 1

  for cfg in adp.configs:
    blk = dev.get_block(cfg.inst.block)
    bl_mode = list(cfg.modes)[0]
    intervals = _get_intervals(dev,dsinfo,cfg)

    for out in blk.outputs:
      if dsinfo.has_interval(cfg.inst,out.name):
        continue

      rel = out.relation[bl_mode]
      try:
        out_interval = ivallib.propagate_intervals(rel,intervals)
        dsinfo.set_interval(cfg.inst,out.name,out_interval)
        count += 1
      except ivallib.UnknownIntervalError as e:
        continue

  return count

def generate_dynamical_system_info(dev,program,adp):
  dsinfo = scalelib.DynamicalSystemInfo()
  ds_ivals = dict(program.intervals())
  for config in adp.configs:
    for stmt in config.stmts_of_type(adplib.ConfigStmtType.PORT):
      if not stmt.source is None:
        ival = ivallib.propagate_intervals(stmt.source,ds_ivals)
        dsinfo.set_interval(config.inst,stmt.name,ival)

    for datum in config.stmts_of_type(adplib.ConfigStmtType.CONSTANT):
      ival = ivallib.Interval.type_infer(datum.value,datum.value)
      dsinfo.set_interval(config.inst,datum.name,ival)

  while _generate_dsinfo_backprop(dev,dsinfo,adp) > 0:
    pass

  while _generate_dsinfo_recurse(dev,dsinfo,adp) > 0:
    pass

  return dsinfo

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

def generate_relation_coeffs(hwinfo,inst,output,baseline_mode,modes,templ):
  valid_modes = []
  if templ.op == baseoplib.OpType.INTEG:
    deriv_coeff_var = scalelib.ConstCoeffVar(inst,output,0)
    ic_coeff_var = scalelib.ConstCoeffVar(inst,output,1)

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


  else:
    coeff_var = scalelib.ConstCoeffVar(inst,output,0)
    for mode in modes:
      targ= hwinfo.get_relation(inst,mode,output)
      succ,coeff,expr = templatize(templ,targ)
      if succ:
        yield scalelib.SCModeImplies(scalelib.ModeVar(inst), \
                                     modes,mode,coeff_var,coeff)
        valid_modes.append(mode)


  yield scalelib.SCSubsetOfModes(scalelib.ModeVar(inst), \
                                 valid_modes, \
                                 modes)


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
  for cstr in generate_relation_coeffs(hwinfo,inst,output, \
                                       baseline_mode,modes,templ):
    yield cstr

  if templ.op == baseoplib.OpType.INTEG:
    _,bl_deriv_expr = get_expr_coefficient(templ.deriv)
    _,bl_ic_expr = get_expr_coefficient(templ.init_cond)
    deriv_coeff_var = scalelib.ConstCoeffVar(inst,output,0)
    ic_coeff_var = scalelib.ConstCoeffVar(inst,output,1)

    # produce necessary factor constraints
    deriv_cstrs,bl_deriv_monom = generate_factor_constraints(inst, \
                                                       bl_deriv_expr)
    ic_cstrs,bl_ic_monom = generate_factor_constraints(inst,bl_ic_expr)

    for cstr in deriv_cstrs + ic_cstrs:
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

def generate_port_properties(hwinfo,dsinfo,inst, \
                                baseline_mode, modes, port):
  oprange = hwinfo.get_op_range(inst,baseline_mode,port)
  quantize = hwinfo.get_quantize(inst,baseline_mode,port)
  freq = hwinfo.get_freq(inst,baseline_mode,port)

  v_mode = scalelib.ModeVar(inst)
  v_lower = scalelib.PropertyVar(scalelib.PropertyVar.Type.INTERVAL_LOWER, \
                                 inst,port)
  v_upper = scalelib.PropertyVar(scalelib.PropertyVar.Type.INTERVAL_UPPER, \
                                 inst,port)
  v_quantize,v_freq = None,None
  if not quantize is None:
    v_quantize = scalelib.PropertyVar(scalelib.PropertyVar.Type.QUANTIZE, \
                                      inst,port)
  if not freq is None:
    v_freq = scalelib.PropertyVar(scalelib.PropertyVar.Type.QUANTIZE, \
                                  inst,port)

  for mode in modes:
    mode_oprange = hwinfo.get_op_range(inst,mode,port)
    lv,uv = mode_oprange.ratio(oprange)
    yield scalelib.SCModeImplies(v_mode,modes,mode,v_lower,lv)
    yield scalelib.SCModeImplies(v_mode,modes,mode,v_upper,uv)
    if not quantize is None:
      mode_quantize= hwinfo.get_quantize(inst,mode,port)
      quant_ratio = mode_quantize.error(mode_oprange)/quantize.error(oprange)
      assert(quant_ratio > 0.0)
      yield scalelib.SCModeImplies(v_mode,modes,mode,v_quantize, quant_ratio)

def generate_port_oprange_constraints(hwinfo, dsinfo,inst,  \
                                             baseline_mode, modes, \
                                             port):
  # encode mode-dependent interval changes
  oprange = hwinfo.get_op_range(inst,baseline_mode,port)
  v_mode = scalelib.ModeVar(inst)
  v_lower = scalelib.PropertyVar(scalelib.PropertyVar.Type.INTERVAL_LOWER, \
                                 inst,port)
  v_upper = scalelib.PropertyVar(scalelib.PropertyVar.Type.INTERVAL_UPPER, \
                                 inst,port)

  v_scalevar = scalelib.PortScaleVar(inst,port)

  interval = dsinfo.get_interval(inst,port)
  cstr = scalelib.SCIntervalCover(interval,oprange)
  cstr.monom.lower.add_term(v_lower)
  cstr.monom.upper.add_term(v_upper)
  cstr.submonom.lower.add_term(v_scalevar)
  cstr.submonom.upper.add_term(v_scalevar)
  yield cstr

def generate_port_quantize_constraints(hwinfo, dsinfo,inst,  \
                                       baseline_mode, modes, \
                                       port):
  v_scalevar = scalelib.PortScaleVar(inst,port)
  v_quantize = scalelib.PropertyVar(scalelib.PropertyVar.Type.QUANTIZE, \
                                 inst,port)

  interval = dsinfo.get_interval(inst,port)
  oprange = hwinfo.get_op_range(inst,baseline_mode,port)
  quantize_error = hwinfo.get_quantize(inst,baseline_mode,port) \
                         .error(oprange)
  cstr = scalelib.SCIntervalCover(ivallib.Interval.type_infer(quantize_error, \
                                                              quantize_error), \
                                  ivallib.Interval.type_infer(abs(interval.lower), \
                                                              abs(interval.upper)))

  if cstr.interval.is_value(0.0):
    return

  cstr.submonom.lower.add_term(v_quantize)
  cstr.submonom.upper.add_term(v_quantize)
  cstr.monom.lower.add_term(v_scalevar)
  cstr.monom.upper.add_term(v_scalevar)
  yield cstr


def generate_port_noise_constraints(hwinfo, dsinfo,inst,  \
                                    baseline_mode, modes, \
                                    port):
  v_scalevar = scalelib.PortScaleVar(inst,port)
  v_lower = scalelib.PropertyVar(scalelib.PropertyVar.Type.INTERVAL_LOWER, \
                                 inst,port)
  v_upper = scalelib.PropertyVar(scalelib.PropertyVar.Type.INTERVAL_UPPER, \
                                 inst,port)

  interval = dsinfo.get_interval(inst,port)
  cstr = scalelib.SCIntervalCover(ivallib.Interval.type_infer(1,1), \
                                  ivallib.Interval.type_infer(abs(interval.lower), \
                                                              abs(interval.upper)))
  cstr.monom.lower.add_term(v_scalevar)
  cstr.monom.lower.add_term(v_lower,-1.0)
  cstr.monom.upper.add_term(v_scalevar)
  cstr.monom.upper.add_term(v_upper,-1.0)
  qual = scalelib.QualityVar()
  cstr.submonom.lower.add_term(qual)
  cstr.submonom.upper.add_term(qual)
  yield cstr

def generate_const_data_field_constraints(hwinfo,dsinfo,inst, \
                                          baseline_mode,modes,datafield):
  for cstr in generate_port_properties(hwinfo, \
                                       dsinfo, \
                                       inst, \
                                       baseline_mode, \
                                       modes, \
                                       datafield):
    yield cstr

  for cstr in generate_port_oprange_constraints(hwinfo, \
                                                dsinfo, \
                                                inst, \
                                                baseline_mode, \
                                                modes, \
                                                datafield):
    yield cstr

  for cstr in generate_port_quantize_constraints(hwinfo, \
                                                 dsinfo, \
                                                 inst, \
                                                 baseline_mode, \
                                                 modes, \
                                                 datafield):
    yield cstr



def generate_digital_port_constraints(hwinfo,dsinfo,inst, \
                                      baseline_mode,modes,port):
  for cstr in generate_port_properties(hwinfo, \
                                       dsinfo, \
                                       config.inst, \
                                       config.modes[0], \
                                       block.modes,
                                       port.name):
    yield cstr

  for cstr in generate_port_oprange_constraints(hwinfo, \
                                                dsinfo, \
                                                config.inst, \
                                                config.modes[0], \
                                                block.modes,
                                                port.name):
    yield cstr

  for cstr in generate_port_quantize_constraints(hwinfo, \
                                                dsinfo, \
                                                config.inst, \
                                                config.modes[0], \
                                                block.modes,
                                                port.name):
    yield cstr



def generate_analog_port_constraints(hwinfo,dsinfo,inst, \
                                     baseline_mode,modes,port):

  for cstr in generate_port_properties(hwinfo, \
                                       dsinfo, \
                                       inst, \
                                       baseline_mode, \
                                       modes,
                                       port):
    yield cstr

  for cstr in generate_port_oprange_constraints(hwinfo, \
                                                dsinfo, \
                                                inst, \
                                                baseline_mode, \
                                                modes,
                                                port):
    yield cstr

  for cstr in generate_port_noise_constraints(hwinfo, \
                                              dsinfo, \
                                              inst, \
                                              baseline_mode, \
                                              modes, port):
    yield cstr






def generate_constraint_problem(dev,program,adp):
  hwinfo = scalelib.HardwareInfo(dev)
  dsinfo = generate_dynamical_system_info(dev,program,adp)

  for conn in adp.conns:
    yield scalelib.SCEq(scalelib.PortScaleVar(conn.source_inst,conn.source_port), \
               scalelib.PortScaleVar(conn.dest_inst, conn.dest_port))

  for config in adp.configs:
    mode_var = scalelib.ModeVar(config.inst)
    block = dev.get_block(config.inst.block)
    # identify which modes can be templatized
    for out in block.outputs:
      # ensure the expression is factorable
      for cstr in templatize_and_factor_relation(hwinfo,
                                      config.inst, \
                                      out.name, \
                                      config.modes[0],
                                      block.modes):
        yield cstr


    for port in list(block.outputs) + list(block.inputs):
      if not adp.port_in_use(config.inst,port.name):
        continue

      if port.type == blocklib.BlockSignalType.ANALOG:
        for cstr in generate_analog_port_constraints(hwinfo, \
                                             dsinfo, \
                                             config.inst, \
                                             config.modes[0], \
                                             block.modes,
                                             port.name):
          yield cstr

      if port.type == blocklib.BlockSignalType.DIGITAL:
        for cstr in generate_digital_port_constraints(hwinfo, \
                                                      dsinfo, \
                                                      config.inst, \
                                                      config.modes[0], \
                                                      block.modes,  \
                                                      port.name):
          yield cstr

    # any data-specific constraints
    for mode in block.modes:
      for datum in block.data:
        if datum.type == blocklib.BlockDataType.CONST:
          for cstr in generate_const_data_field_constraints(hwinfo, \
                                                        dsinfo, \
                                                        config.inst, \
                                                        config.modes[0], \
                                                        block.modes,  \
                                                        datum.name):
            yield cstr

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


def get_objective():
  qual = scalelib.QualityVar()

  monom = scalelib.SCMonomial()
  monom.add_term(qual,-1.0)
  return monom

def scale(dev, program, adp):
  cstr_prob = []
  for stmt in generate_constraint_problem(dev,program,adp):
    cstr_prob.append(stmt)

  obj = get_objective()
  for adp in lscale_solver.solve(dev,adp,cstr_prob,obj):
    yield adp

