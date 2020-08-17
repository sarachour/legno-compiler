import ops.interval as ivallib
from enum import Enum

class ScaleMethod:
  IDEAL = "ideal"
  PHYSICAL = "physical"

class DynamicalSystemInfo:

  def __init__(self):
    self.intervals = {}

  def set_interval(self,inst,port,ival):
    print("%s.%s = %s" % (inst,port,ival))
    assert(isinstance(ival,ivallib.Interval))
    self.intervals[(str(inst),port)] = ival

  def has_interval(self,inst,port):
    return (str(inst),port) in self.intervals

  def get_interval(self,inst,port):
    if not self.has_interval(inst,port):
      raise Exception("no interval <%s,%s>" % (inst,port))
    return self.intervals[(str(inst),port)]

class HardwareInfo:

  def __init__(self,dev,scale_method=ScaleMethod.IDEAL):
    self.dev = dev
    self.scale_method = scale_method

  def _get_port(self,instance,name):
    blk = self.dev.get_block(instance.block)
    if blk.inputs.has(name):
      return blk.inputs[name]
    else:
      return blk.outputs[name]

  def get_op_range(self,instance,mode,port_name):
    assert(isinstance(port_name,str))
    port = self._get_port(instance,port_name)
    ival = port.interval[mode]
    if ival is None:
      raise Exception("specification error: %s.%s has no operating range for mode %s" % (instance,port_name,mode))
    return ival

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

  def vars(self):
    return [self]

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
    self.index = index

  def __repr__(self):
    return "coeff(%s,%s).%d" % (self.inst, \
                                self.port, \
                                self.index)

class PropertyVar(SCVar):
  class Type(Enum):
    FREQUENCY = "freq"
    INTERVAL_UPPER = "ivalU"
    INTERVAL_LOWER = "ivalL"

  def __init__(self,type,instance,port):
    assert(isinstance(type,PropertyVar.Type))
    SCVar.__init__(self)
    self.type = type
    self.inst = instance
    self.port = port

  def __repr__(self):
    return "prop.%s(%s,%s)" \
      % (self.type.value,self.inst,self.port)

class SCMonomial:

  def __init__(self):
    self._coeff =  1.0
    self._terms = []
    self._expos = []

  def vars(self):
    for t in self._terms:
      yield t

  def copy(self):
    monom = SCMonomial()
    monom.coeff = self.coeff
    for t,e in self.terms:
      monom.add_term(t,e)
    return monom

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
    if self.coeff != 1.0 or len(self._terms) == 0:
      st = ["%.3f" % self.coeff]
    else:
      st = []

    for t,e in zip(self._terms,self._expos):
      if e != 1.0:
        st.append("(%s^%.3f)" % (t,e))
      else:
        st.append("(%s)" % t)

    return "*".join(st)

class SCSubsetEq:

  def __init__(self,lhs_expr,lhs_interval,rhs_expr,rhs_interval):
    assert(isinstance(lhs,SCMonomial) or \
           isinstance(lhs,SCVar))
    self.lhs_expr = lhs_expr
    self.lhs_interval = lhs_interval
    self.rhs_expr = rhs_expr
    self.rhs_interval = rhs_interval


  def vars(self):
    for var in self.lhs_expr.vars():
      yield var

    for var in self.rhs_expr.vars():
      yield var



class SCEq:

  def __init__(self,lhs,rhs):
    assert(isinstance(lhs,SCMonomial) or \
           isinstance(lhs,SCVar))
    assert(isinstance(rhs,SCMonomial) or \
           isinstance(rhs,SCVar))

    self.lhs = lhs
    self.rhs = rhs

  def vars(self):
    for var in self.lhs.vars():
      yield var

    for var in self.rhs.vars():
      yield var


  def __repr__(self):
    return "%s == %s" % (self.lhs,self.rhs)

class SCObserve:

  def __init__(self,monom):
    assert(isinstance(monom,SCMonomial))
    self.monomial

  def vars(self):
    for var in self.monomial.vars():
      yield var


  def __repr__(self):
    return "observe(%s)" % self.monomial

class SCIntervalMonomial:

    def __init__(self):
      self.lower = SCMonomial()
      self.upper = SCMonomial()

    def vars(self):
      for v in self.lower.vars():
        yield v
      for v in self.upper.vars():
        yield v

    def __repr__(self):
      return "[%s,%s]" % (self.lower,self.upper)

class SCIntervalCover:

  def __init__(self,subinterval,interval):
    assert(isinstance(subinterval,ivallib.Interval))
    assert(isinstance(interval,ivallib.Interval))
    self.subinterval = subinterval
    self.interval = interval
    self.submonom = SCIntervalMonomial()
    self.monom = SCIntervalMonomial()

  def valid(self):
    if self.subinterval.upper == 0 or \
       self.subinterval.lower == 0:
      raise Exception("not handled: subinterval %s" % self.subinterval)

    if self.interval.upper == 0 or \
       self.interval.lower == 0:
      raise Exception("not handled: interval %s" % self.interval)

    if self.subinterval.upper > 0 and \
       self.interval.upper < 0:
      return False
    if self.subinterval.lower < 0 and \
       self.interval.lower > 0:
      return False
    return True

  def trivial(self):
    upper_trivial,lower_trivial = False,False
    if self.subinterval.upper < 0 and \
       self.interval.upper > 0:
      upper_trivial = True

    if self.subinterval.lower > 0 and \
       self.subinterval.lower < 0:
      lower_trivial = True
    return (lower_trivial,upper_trivial)


  def vars(self):
    for v in self.submonom.vars():
      yield v
    for v in self.monom.vars():
      yield v


  def __repr__(self):
    st = "%s*%s" % (self.submonom,self.subinterval)
    st += " SUBSETEQ "
    st += "%s*%s" % (self.monom,self.interval)
    return st

class SCSubsetOfModes:
  def __init__(self,modevar,modes,all_modes):
    assert(isinstance(modevar,ModeVar))
    self.mode_var = modevar
    self.modes = list(all_modes)
    self.valid_modes = list(modes)

  def vars(self):
    yield self.mode_var

  def __repr__(self):
    return "%s IN %s SUBSET %s"  \
      % (self.mode_var,self.valid_modes,self.modes)

class SCModeImplies:

  def __init__(self,modevar,all_modes,mode,dep_var,value):
    assert(isinstance(modevar,ModeVar))
    assert(isinstance(value,float))
    assert(isinstance(dep_var,ConstCoeffVar) or \
           isinstance(dep_var,PropertyVar))
    self.mode_var = modevar
    self.mode = mode
    self.modes = list(all_modes)
    self.dep_var = dep_var
    self.value = value

  def vars(self):
    yield self.mode_var
    yield self.dep_var

  def __repr__(self):
    return "%s == %s :> %s = %s" % (self.mode_var,self.mode, \
                                    self.dep_var,self.value)

