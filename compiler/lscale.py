import hwlib.adp as adplib
import hwlib.block as blocklib
import ops.base_op as baseoplib

class ScaleMethod:
  IDEAL = "ideal"
  PHYSICAL = "physical"

class DynamicalSystemInfo:

  def __init__(self):
    self.intervals = {}

class HardwareInfo:

  def __init__(self,dev,scale_method=ScaleMethod.IDEAL):
    self.dev = dev
    self.scale_method = scale_method


  def get_relation(self,instance,mode,port):
    out = self.dev.get_block(instance.block) \
                  .outputs[port]
    if self.scale_method == ScaleMethod.IDEAL:
      assert(out.relation.has(mode))
      return out.relation[mode]
    else:
      delta = out.deltas[mode]
      raise Exception("get_relation")

class SCVar:

  def __init__(self):
    pass

class ModeVar(SCVar):

  def __init__(self,instance):
    SCVar.__init__(self)
    self.inst = instance

  def __repr__(self):
    return "mode(%s)" % self.inst

class PortScaleVar(SCVar):

  def __init__(self,instance,port):
    SCVar.__init__(self)
    self.inst = instance
    self.port = port

  def __repr__(self):
    return "port(%s,%s)" \
      % (self.inst,self.port)

class TimeScaleVar(SCVar):

  def __init__(self):
    SCVar.__init__(self)
    pass

  def __repr__(self):
    return "tau"


class ConstCoeffVar(SCVar):

  def __init__(self,instance,port,index):
    self.inst = instance
    self.port = port
    self.index = ConstCoeffVar.INDEX
    ConstCoeffVar.INDEX + 1

class PropertyVar(SCVar):
  class Type:
    FREQUENCY = "freq"
    INTERVAL = "interval"

  def __init__(self,type,instance,port):
    SCVar.__init__(self)
    self.type = type
    self.inst = instance
    self.port = port

class SCMonomial:

  def __init__(self):
    self._coeff =  1.0
    self._terms = []
    self._expos = []

  @property
  def coeff(self):
    return self._coeff

  @coeff.setter
  def coeff(self,c):
    assert(c > 0)
    self._coeff = c

  def product(self,mono):
    assert(isinstance(mono,SCMonomial))
    self.coeff *= mono.coeff
    for term,expo in mono.terms:
      self.add_term(term,expo)

  def add_term(self,term,expo=1.0):
    assert(isinstance(term,SCVar))
    assert(isinstance(expo,float))
    self._terms.append(term)
    self._expos.append(expo)

  @staticmethod
  def make_var(v):
    m = SCMonomial()
    m.add_term(v,1.0)
    return m

  @staticmethod
  def make_const(value):
    m = SCMonomial()
    m.coeff = value
    return m

  @property
  def terms(self):
    for t,e in zip(self._terms,self._expos):
      yield t,e

  def __repr__(self):
    st = ["%f" % self.coeff]
    for t,e in zip(self._terms,self._expos):
      st.append("(%s^%f)" % (t,e))
    return "*".join(st)

class SCSubsetEq:

  def __init__(self,lhs_expr,lhs_interval,rhs_expr,rhs_interval):
    assert(isinstance(lhs,SCMonomial) or \
           isinstance(lhs,SCVar))
    self.lhs_expr = lhs_expr
    self.lhs_interval = lhs_interval
    self.rhs_expr = rhs_expr
    self.rhs_interval = rhs_interval



class SCEq:

  def __init__(self,lhs,rhs):
    assert(isinstance(lhs,SCMonomial) or \
           isinstance(lhs,SCVar))
    assert(isinstance(rhs,SCMonomial) or \
           isinstance(rhs,SCVar))

    self.lhs = lhs
    self.rhs = rhs

  def __repr__(self):
    return "%s == %s" % (self.lhs,self.rhs)

def generate_dynamical_system_info(program,adp):
  ivals = DynamicalSystemInfo()
  for config in adp.configs:
    for stmt in config.stmts_of_type(adplib.ConfigStmtType.PORT):
      print(stmt)

  return ivals

def templatize_relation(templ,modes):
  '''
  Create a relation with ConstVars instead of coefficients.
  Divide each mode relation by the baseline. If the shape doesn't match
  up, raise an exception
  '''
  raise Exception("templatize %s for %s" % (templ,modes))

def generate_factor_constraints(inst,rel):
  if rel.op == baseoplib.OpType.INTEG:
    c1,mderiv = generate_factor_constraints(inst,rel.deriv)
    c2,mic = generate_factor_constraints(inst,rel.init_cond)
    monomial = SCMonomial()
    monomial.product(mderiv)
    monomial.add_term(TimeScaleVar())
    cspeed = SCEq(monomial,mic)
    return c1+c2+[cspeed],mic

  if rel.op == baseoplib.OpType.VAR:
    variable = PortScaleVar(inst,rel.name)
    return [],SCMonomial.make_var(variable)

  if rel.op == baseoplib.OpType.CONST:
    return [],SCMonomial.make_const(rel.value)

  if rel.op == baseoplib.OpType.MULT:
    c1,op1 = generate_factor_constraints(inst,rel.arg(0))
    c2,op2 = generate_factor_constraints(inst,rel.arg(1))
    m = SCMonomial()
    m.product(op1)
    m.product(op2)
    return c1+c2,m
  else:
    raise Exception(rel)

def generate_constraint_problem(dev,program,adp):
  dsinfo = generate_dynamical_system_info(program,adp)
  hwinfo = HardwareInfo(dev)

  for conn in adp.conns:
    yield SCEq(PortScaleVar(conn.source_inst,conn.source_port), \
               PortScaleVar(conn.dest_inst, conn.dest_port))

  for config in adp.configs:
    mode_var = ModeVar(config.inst)
    block = dev.get_block(config.inst.block)
    valid_modes = set(block.modes)
    # identify which modes can be templatized
    for out in block.outputs:
      cstr,modes,rel = templatize_relation(block.outputs[out.name] \
                                     .relation[config.modes[0]],
                                block.modes)
      for cstr in cstrs:
        yield cstr

      # ensure the expression is factorable
      cstrs, scexpr = generate_factor_constraints(config.inst,rel)
      for cstr in cstrs:
        yield cstr

      yield SCEq(PortScaleVar(config.inst,out.name), scexpr)
      valid_modes = valid_modes.intersection(modes)

    # any data-specific constraints
    for mode in valid_modes:
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
  for stmt in generate_constraint_problem(dev,program,adp):
    print(stmt)
  raise NotImplementedError
