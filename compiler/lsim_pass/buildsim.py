import ops.base_op as baseoplib
import ops.generic_op as genoplib
import ops.op as oplib
import hwlib.adp as adplib

import compiler.math_utils as mathutils

class ADPSim:

  class Var:

    def __init__(self,inst,port):
      assert(isinstance(port,str))
      assert(isinstance(inst,adplib.BlockInst))
      self.inst = inst
      self.port = port

    def __eq__(self,other):
      assert(isinstance(other,ADPSim.Var))
      return self.port == other.port and \
        self.inst == other.inst

    def __repr__(self):
      return "%s.%s" % (self.inst,self.port)

    @property
    def var_name(self):
      return "%s_%s" % (self.inst,self.port)

    @property
    def key(self):
      return str(self)

  def __init__(self):
    self._state_vars = []
    self.init_conds = {}
    self.derivs = {}
    self.sources = {}
    self.scfs = {}
    self.time_scale = 1.0

  def is_state_var(self,inst,port):
    return ADPSim.Var(inst,port) in self._state_vars

  def state_var(self,inst,port):
    idx = self._state_vars.index(ADPSim.Var(inst,port))
    return self._state_vars[idx]

  def decl_stvar(self,inst,port):
    v = ADPSim.Var(inst,port)
    self._state_vars.append(v)

  def set_stvar(self,inst,port,deriv,ic,source=None,scf=1.0):
    var = ADPSim.Var(inst,port)
    assert(self.is_state_var(inst,port))
    self.init_conds[var.key] = oplib.to_python(ic)
    self.derivs[var.key] = oplib.to_python(deriv)
    self.sources[var.key] = source
    self.scfs[var.key] = scf

  def scale_factor(self,var):
    return self.scfs[var.key]

  def derivative(self,var):
    return self.derivs[var.key][1]

  def initial_cond(self,var):
    return self.init_conds[var.key][1]

  def state_variables(self):
    return self._state_vars

  def __repr__(self):
    st = ""
    for stvar in self._state_vars:
      st += "=== State Var %s (%s) ===\n" % (stvar,self.sources[stvar.key])
      st += "deriv: %s\n" % self.derivs[stvar.key][1]
      st += "initc: %s\n" % self.init_conds[stvar.key][1]

    return st

def identify_integrators(dev):
  integs = []
  for blk in dev.blocks:
    for mode in blk.modes:
      for out in blk.outputs:
        expr = out.relation[mode]
        is_integ = any(filter(lambda n: n.op == baseoplib.OpType.INTEG, \
                              expr.nodes()))
        if is_integ:
          integs.append((blk.name,mode,out.name))

  return integs

def build_const_data_field(dev,adp,cfg,field):
  blk = dev.get_block(cfg.inst.block)
  spec = blk.data[field.name]
  dig_val = spec.round_value(cfg.mode, \
                       field.value*field.scf)
  return genoplib.Const(dig_val)

def build_expr_data_field(dev,adp,cfg,field):
  blk = dev.get_block(cfg.inst.block)
  spec = blk.data[field.name]
  inject_coeff = genoplib.Const(field.injs[field.name])
  inject_inps = {}
  for inp in spec.inputs:
    inject_inps[inp] = genoplib.Mult( \
                                      genoplib.Const(field.injs[inp]), \
                                      genoplib.Var(inp))

  conc = genoplib.Mult(inject_coeff, \
                       field.expr.substitute(inject_inps))
  return conc


def build_expr(dev,sim,adp,cfg,expr):
  blk = dev.get_block(cfg.inst.block)
  repl = {}
  for var in expr.vars():
    if cfg[var].type == adplib.ConfigStmtType.CONSTANT:
      repl[var] = build_const_data_field(dev,adp,cfg,cfg[var])
    elif cfg[var].type == adplib.ConfigStmtType.EXPR:
      repl[var] = build_expr_data_field(dev,adp,cfg,cfg[var])
    elif cfg[var].type == adplib.ConfigStmtType.PORT:
      terms = []
      # get source expressions
      for inst,port in map(lambda c: (c.source_inst,c.source_port), \
                           filter(lambda c: c.dest_inst == cfg.inst and \
                                  c.dest_port == var, \
                                  adp.conns)):
        if sim.is_state_var(inst,port):
          terms.append(genoplib.Var(sim.state_var(inst,port).var_name))
          continue
        else:
          print("not stvar: %s.%s" % (inst,port))

        src_cfg = adp.configs.get(inst.block,inst.loc)
        src_blk = dev.get_block(inst.block)
        src_rel = src_blk.outputs[port].relation[src_cfg.mode]
        terms.append(build_expr(dev,sim,adp,src_cfg,src_rel))

      repl[var] = genoplib.sum(terms)
    else:
      raise Exception("unknown type: %s" % (cfg[var].type))

  conc_expr = expr.substitute(repl)
  return conc_expr

def build_diffeqs(dev,adp):
  integs = identify_integrators(dev)
  sim = ADPSim()
  for cfg in adp.configs:
    blk = dev.get_block(cfg.inst.block)
    for port in cfg.stmts_of_type(adplib.ConfigStmtType.PORT):
      if (cfg.inst.block,cfg.mode,port.name) in integs:
        sim.decl_stvar(cfg.inst,port.name)

  for cfg in adp.configs:
    blk = dev.get_block(cfg.inst.block)
    for port in cfg.stmts_of_type(adplib.ConfigStmtType.PORT):
      if (cfg.inst.block,cfg.mode,port.name) in integs:
        expr = blk.outputs[port.name].relation[cfg.mode]
        integ_expr = mathutils.canonicalize_integration_operation(expr)

        deriv = build_expr(dev,sim,adp,cfg,integ_expr.deriv)
        init_cond = build_expr(dev,sim,adp,cfg,integ_expr.init_cond)

        assert(integ_expr.op == baseoplib.OpType.INTEG)
        sim.set_stvar(cfg.inst,port.name, \
                      deriv, \
                      init_cond, \
                      source=port.source, \
                      scf=port.scf)

  return sim

def build_simulation(dev,adp):
  sim = build_diffeqs(dev,adp)
  sim.time_scale = adp.tau
  print(sim)
  return sim
