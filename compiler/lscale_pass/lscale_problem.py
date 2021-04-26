import hwlib.adp as adplib
import hwlib.block as blocklib
import ops.base_op as baseoplib
import ops.generic_op as genoplib
import ops.opparse as opparse
import numpy as np
import compiler.lscale_pass.lscale_ops as scalelib
import compiler.lscale_pass.lscale_harmonize as harmlib
import compiler.lscale_pass.lscale_dynsys as scaledslib
import compiler.math_utils as mathutils

import ops.interval as ivallib


def generate_factor_constraints(inst,rel):

  if rel.op == baseoplib.OpType.INTEG:
    c1,mderiv = generate_factor_constraints(inst,rel.deriv)
    c2,mic = generate_factor_constraints(inst,rel.init_cond)
    monomial = scalelib.SCMonomial()
    monomial.product(mderiv)
    monomial.add_term(scalelib.TimeScaleVar(),-1)
    cspeed = scalelib.SCEq(monomial,mic)
    return c1+c2+[cspeed],mic

  elif rel.op == baseoplib.OpType.VAR and \
     harmlib.is_gain_var(rel.name):
    idx = harmlib.from_gain_var(rel.name)
    return [],scalelib.SCMonomial \
                      .make_var(scalelib.ConstCoeffVar(inst,idx))

  elif rel.op == baseoplib.OpType.VAR:
    variable = scalelib.PortScaleVar(inst,rel.name)
    return [],scalelib.SCMonomial.make_var(variable)

  elif rel.op == baseoplib.OpType.CONST:
    return [],scalelib.SCMonomial.make_const(abs(rel.value))


  elif rel.op == baseoplib.OpType.MULT:
    c1,op1 = generate_factor_constraints(inst,rel.arg(0))
    c2,op2 = generate_factor_constraints(inst,rel.arg(1))
    m = scalelib.SCMonomial()
    m.product(op1)
    m.product(op2)
    return c1+c2,m

  elif rel.op == baseoplib.OpType.EMIT:
    c,op = generate_factor_constraints(inst,rel.arg(0))

    return c,op

  elif rel.op == baseoplib.OpType.CALL:
    assert(rel.func.expr.op == baseoplib.OpType.VAR)
    data_field_name = rel.func.expr.name

    cstrs = []
    # make sure each constraint is
    assert(len(rel.func.func_args) == len(rel.values))
    for arg_name,value in zip(rel.func.func_args,rel.values):
      func_arg = scalelib.FuncArgScaleVar(inst,rel.func.expr.name,arg_name)
      subcstrs,arg_scexpr = generate_factor_constraints(inst,value)

      cstrs.append(scalelib.SCEq(scalelib.SCMonomial.make_var(func_arg), \
                        arg_scexpr))

      func_arg_inj = scalelib.InjectVar(inst,data_field_name,arg_name)
      monom = scalelib.SCMonomial()
      monom.add_term(func_arg)
      monom.add_term(func_arg_inj)
      cstrs.append(scalelib.SCEq(monom,  \
                                 scalelib.SCMonomial.make_const(1.0)))
      cstrs += subcstrs

    out_inj = scalelib.InjectVar(inst,data_field_name,None)
    out_var = scalelib.FuncArgScaleVar(inst,rel.func.expr.name,None)
    cstrs.append(scalelib.SCEq(scalelib.SCMonomial.make_var(out_inj),  \
                 scalelib.SCMonomial.make_var(out_var)))

    return cstrs,scalelib.SCMonomial.make_var(out_var)

  else:
    raise Exception(rel)


def generate_port_properties(hwinfo,dsinfo,inst, \
                             baseline_mode, modes, port):
  oprange = hwinfo.get_op_range(inst,baseline_mode,port)
  quantize = hwinfo.get_quantize(inst,baseline_mode,port)
  noise = hwinfo.get_noise(inst,baseline_mode,port)
  freq = hwinfo.get_freq_limit(inst,baseline_mode,port)

  v_mode = scalelib.ModeVar(inst,hwinfo.modes(inst.block))
  v_lower = scalelib.PropertyVar(scalelib.PropertyVar.Type.INTERVAL_LOWER, \
                                 inst,port)
  v_upper = scalelib.PropertyVar(scalelib.PropertyVar.Type.INTERVAL_UPPER, \
                                 inst,port)
  v_quantize,v_freq = None,None
  if not quantize is None:
    v_quantize = scalelib.PropertyVar(scalelib.PropertyVar.Type.QUANTIZE, \
                                      inst,port)
  if not freq is None:
    v_freq = scalelib.PropertyVar(scalelib.PropertyVar.Type.MAXFREQ, \
                                  inst,port)

  if not noise is None:
    v_noise = scalelib.PropertyVar(scalelib.PropertyVar.Type.NOISE, \
                                   inst,port)

  for mode in modes:
    mode_oprange = hwinfo.get_op_range(inst,mode,port)
    lv,uv = mode_oprange.ratio(oprange)
    yield scalelib.SCModeImplies(v_mode,mode,v_lower,lv)
    yield scalelib.SCModeImplies(v_mode,mode,v_upper,uv)

    if not quantize is None:
      mode_quantize= hwinfo.get_quantize(inst,mode,port)
      quant_ratio = mode_quantize.error(mode_oprange)/quantize.error(oprange)
      quant_ratio *= mode_quantize.scale
      assert(quant_ratio > 0.0)
      yield scalelib.SCModeImplies(v_mode,mode,v_quantize, quant_ratio)

    if not noise is None:
      mode_noise= hwinfo.get_noise(inst,mode,port)
      noise_ratio = mode_noise / noise
      assert(noise_ratio > 0.0)
      yield scalelib.SCModeImplies(v_mode,mode,v_noise,noise_ratio)

    if not freq is None:
      mode_freq = hwinfo.get_freq_limit(inst,mode,port)
      freq_ratio = mode_freq / freq
      assert(freq_ratio > 0.0)
      yield scalelib.SCModeImplies(v_mode,mode,v_freq,freq_ratio)


def generate_port_freq_limit_constraints(hwinfo,dsinfo,inst, \
                                         baseline_mode,modes, \
                                         port):
  v_freq_limit = scalelib.PropertyVar(scalelib.PropertyVar.Type.MAXFREQ, \
                                 inst,port)
  baseline_freq_limit = hwinfo.get_freq_limit(inst,baseline_mode,port)
  if baseline_freq_limit is None:
    return

  v_scalevar = scalelib.TimeScaleVar()

  curr_freq = scalelib.SCMonomial()
  curr_freq.coeff = hwinfo.get_board_frequency()
  curr_freq.add_term(v_scalevar)

  max_freq = scalelib.SCMonomial()
  max_freq.coeff = baseline_freq_limit
  max_freq.add_term(v_freq_limit)
  yield scalelib.SCLTE(curr_freq,max_freq)

def generate_port_oprange_constraints(hwinfo,dsinfo,inst,  \
                                      baseline_mode,modes, \
                                      port):
  # encode mode-dependent interval changes
  oprange = hwinfo.get_op_range(inst,baseline_mode,port)
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
                                       port,lower=False, \
                                       digital_expr=False):


  v_scalevar = scalelib.PortScaleVar(inst,port)
  v_quantize = scalelib.PropertyVar(scalelib.PropertyVar.Type.QUANTIZE, \
                                 inst,port)

  interval = dsinfo.get_interval(inst,port)
 
  ampl_val = abs(interval.lower) if lower else abs(interval.upper)

  oprange = hwinfo.get_op_range(inst,baseline_mode,port)
  baseline_quantize_error = hwinfo.get_quantize(inst,baseline_mode,port) \
                         .error(oprange)

  if ampl_val == 0.0:
    return

  #signal
  snr_term = scalelib.SCMonomial()
  snr_term.coeff = ampl_val/baseline_quantize_error
  snr_term.add_term(v_scalevar)
  snr_term.add_term(v_quantize,-1)

  if digital_expr:
    qual = scalelib.QualityVar(scalelib.QualityMeasure.DQME)
  else:
    qual = scalelib.QualityVar(scalelib.QualityMeasure.DQM)
    qmeas = scalelib.SCMonomial()
    qmeas.add_term(v_scalevar)
    qmeas.add_term(v_quantize,-1)
    hwinfo.add_quality_term(scalelib.QualityMeasure.DQM,qmeas)

  cstr = scalelib.SCLTE(qual, \
                        snr_term)

  yield cstr
 

def generate_port_noise_constraints(hwinfo, dsinfo,inst,  \
                                    baseline_mode, modes, \
                                    port,lower=False, \
                                    is_dsvar=False, \
                                    is_obs=False):
  v_scalevar = scalelib.PortScaleVar(inst,port)
  v_noise = scalelib.PropertyVar(scalelib.PropertyVar.Type.NOISE, \
                                 inst,port)

  interval = dsinfo.get_interval(inst,port)
  ampl_val = abs(interval.lower) if lower else abs(interval.upper)

  if ampl_val == 0.0:
    return


  baseline_noise = hwinfo.get_noise(inst,baseline_mode,port)

  if baseline_noise is None:
    print("[WARN] no noise defined: %s" % inst)
    return

  snr_term = scalelib.SCMonomial()
  snr_term.coeff = ampl_val/baseline_noise
  snr_term.add_term(v_scalevar)
  snr_term.add_term(v_noise,-1)


  qual = scalelib.QualityVar(scalelib.QualityMeasure.AQM)
  cstr = scalelib.SCLTE(qual, \
                        snr_term)

 
  yield cstr

  qmeas = scalelib.SCMonomial()
  qmeas.add_term(v_scalevar)
  qmeas.add_term(v_noise,-1)
  hwinfo.add_quality_term(scalelib.QualityMeasure.AQM,qmeas)

  if is_dsvar:
    qual = scalelib.QualityVar(scalelib.QualityMeasure.AQMST)
    cstr = scalelib.SCLTE(qual, \
                        snr_term)
    yield cstr

  if is_obs:
    qual = scalelib.QualityVar(scalelib.QualityMeasure.AQMOBS)
    cstr = scalelib.SCLTE(qual, \
                        snr_term)
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
                                       inst, \
                                       baseline_mode, \
                                       modes,
                                       port):
    yield cstr

  for cstr in generate_port_freq_limit_constraints(hwinfo, \
                                                   dsinfo, \
                                                   inst, \
                                                   baseline_mode, \
                                                   modes, \
                                                   port):
    yield cstr

  for cstr in generate_port_oprange_constraints(hwinfo, \
                                                dsinfo, \
                                                inst, \
                                                baseline_mode, \
                                                modes,
                                                port):
    yield cstr

  for do_lower in [True,False]:
    for cstr in generate_port_quantize_constraints(hwinfo, \
                                                   dsinfo, \
                                                   inst, \
                                                   baseline_mode, \
                                                   modes,
                                                   port, \
                                                   lower=do_lower, \
                                                   digital_expr=True):
      yield cstr



def generate_analog_port_constraints(hwinfo,dsinfo,inst, \
                                     baseline_mode,modes,port, \
                                     is_dsvar=False, \
                                     is_obs=False):

  for cstr in generate_port_properties(hwinfo, \
                                       dsinfo, \
                                       inst, \
                                       baseline_mode, \
                                       modes,
                                       port):
    yield cstr

  for cstr in generate_port_freq_limit_constraints(hwinfo, \
                                                   dsinfo, \
                                                   inst, \
                                                   baseline_mode, \
                                                   modes, \
                                                   port):
    yield cstr


  for cstr in generate_port_oprange_constraints(hwinfo, \
                                                dsinfo, \
                                                inst, \
                                                baseline_mode, \
                                                modes,
                                                port):
    yield cstr

  for do_lower in [True,False]:
    for cstr in generate_port_noise_constraints(hwinfo, \
                                                dsinfo, \
                                                inst, \
                                                baseline_mode, \
                                                modes, port, \
                                                lower=do_lower, \
                                                is_dsvar=is_dsvar, \
                                                is_obs=is_obs):
      yield cstr


def add_average_quality_terms(hwinfo):
  monom = scalelib.SCMonomial.make_const(1.0)
  n_terms = len(list(hwinfo.get_quality_terms(scalelib.QualityMeasure.AQM)))
  for term in hwinfo.get_quality_terms(scalelib.QualityMeasure.AQM):
    monom.product(term.copy().exponentiate(1.0/n_terms))

  if len(monom) >= 1:
    yield scalelib.SCEq(scalelib.QualityVar(scalelib.QualityMeasure.AVGAQM), monom)

  monom = scalelib.SCMonomial.make_const(1.0)
  n_terms = len(list(hwinfo.get_quality_terms(scalelib.QualityMeasure.DQM)))
  for term in hwinfo.get_quality_terms(scalelib.QualityMeasure.DQM):
    monom.product(term.copy().exponentiate(1.0/n_terms))

  if len(monom) >= 1:
    yield scalelib.SCEq(scalelib.QualityVar(scalelib.QualityMeasure.AVGDQM), monom)


def force_identity_scaling_transform(dev,adp):

  for config in adp.configs:
    block = dev.get_block(config.inst.block)
    for out in block.outputs:
      yield scalelib.SCEq(scalelib.PortScaleVar(config.inst,out.name), \
                          scalelib.SCMonomial.make_const(1.0))

    for inp in block.inputs:
      yield scalelib.SCEq(scalelib.PortScaleVar(config.inst,inp.name), \
                          scalelib.SCMonomial.make_const(1.0))

    for data in block.data:
      yield scalelib.SCEq(scalelib.PortScaleVar(config.inst,data.name), \
                          scalelib.SCMonomial.make_const(1.0))

def restrict_modes_to_lgraph_only(hwinfo,inst,mode_subset):
  v_mode = scalelib.ModeVar(inst,hwinfo.modes(inst.block))
  yield scalelib.SCSubsetOfModes(v_mode,mode_subset)

def generate_constraint_problem(dev,program,adp, \
                                scale_method=scalelib.ScaleMethod.IDEAL, \
                                calib_obj=None, \
                                one_mode=False, \
                                no_scale=False):

  hwinfo = scalelib.HardwareInfo(dev, \
                                 scale_method=scale_method, \
                                 calib_obj=calib_obj)

  dsinfo = scaledslib.generate_dynamical_system_info(dev,program,adp, \
                                                     apply_scale_transform=False)


  if no_scale:
    for cstr in force_identity_scaling_transform(dev,adp):
      yield cstr

  for block in dev.blocks:
    hwinfo.register_modes(block,block.modes)

  for conn in adp.conns:
    yield scalelib.SCEq(scalelib.PortScaleVar(conn.source_inst,conn.source_port), \
               scalelib.PortScaleVar(conn.dest_inst, conn.dest_port))

  for config in adp.configs:
    block = dev.get_block(config.inst.block)
    mode_var = scalelib.ModeVar(config.inst,hwinfo.modes(block.name))

    if one_mode:
      for cstr in restrict_modes_to_lgraph_only(hwinfo,config.inst,config.modes):
        yield cstr

    modes_subset = set(hwinfo.modes(block.name))
    for out in block.outputs:
      # idealized relation
      baseline = hwinfo.get_ideal_relation(config.inst,config.modes[0],out.name)
      deviations = []
      deviation_modes = []
      print(config)
      for mode in hwinfo.modes(block.name):
        try:
           dev_rel = hwinfo.get_empirical_relation(config.inst, \
							    mode, \
							    out.name)
        except Exception as e:
           print("[could not get deviation] %s" % e)
           dev_rel = None

        if not dev_rel is None:
          deviations.append(dev_rel)
          deviation_modes.append(mode)
          print(dev_rel)

      master_rel, modes, mode_assignments = harmlib.get_master_relation(baseline, \
                                                                        deviations, \
                                                                        deviation_modes)
      modes_subset = list(set(modes_subset).intersection(set(modes)))
      cstrs,op_monom = generate_factor_constraints(config.inst,master_rel)
      for cstr in cstrs:
        yield cstr

      yield scalelib.SCEq(scalelib.PortScaleVar(config.inst,out.name), \
                          op_monom)

      for gain_var,values in mode_assignments:
        gain_idx = harmlib.from_gain_var(gain_var)
        for mode,value in values.items():
          yield scalelib.SCModeImplies(scalelib.ModeVar(config.inst,\
                                                        hwinfo.modes(block.name)), \
                                       mode,scalelib.ConstCoeffVar(config.inst, \
                                                                   gain_idx), \
                                       value)



    if len(modes_subset) == 0:
      raise Exception("block %s: no valid modes" % (config.inst))

    yield scalelib.SCSubsetOfModes(scalelib.ModeVar(config.inst, \
                                                    hwinfo.modes(block.name)),\
                                                    modes_subset)

    for port in list(block.outputs) + list(block.inputs):
      if not adp.port_in_use(config.inst,port.name) and not port.extern:
        continue

      is_dsvar = False
      is_obs = False
      # if this is a labelled port, preserve it!!
      if config.has(port.name) and \
         not config[port.name].source is None:
        is_dsvar = True

      if port.extern:
        is_obs = True

      if port.type == blocklib.BlockSignalType.ANALOG:
        for cstr in generate_analog_port_constraints(hwinfo, \
                                                     dsinfo, \
                                                     config.inst, \
                                                     config.modes[0], \
                                                     block.modes,
                                                     port.name, \
                                                     is_dsvar=is_dsvar, \
                                                     is_obs=is_obs):
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

  for cstr in add_average_quality_terms(hwinfo):
    yield cstr


