import runtime.models.exp_delta_model as exp_delta_model_lib
import hwlib.adp as adplib
import ops.interval as ivallib
import ops.generic_op as genoplib
from enum import Enum

class ObjectiveFun(Enum):
  QUALITY = "qty"
  QUALITY_SPEED = "qtytau"
  EMPIRICAL = "emp"
  SPEED = "tau"

class QualityMeasure(Enum):
  AQM = "AQM"
  DQM = "DQM"
  DQME = "DQME"
  AQMST = "AQMST"
  AQMOBS  = "AQMOBS"
  AVGAQM = "AVGAQM"
  AVGDQM = "AVGDQM"


class ScaleMethod(Enum):
  IDEAL = "ideal"
  PHYSICAL = "phys"


class DynamicalSystemInfo:

  def __init__(self):
    self.intervals = {}
    self.exprs = {}

  def set_interval(self,inst,port,ival):
    assert(isinstance(ival,ivallib.Interval))
    self.intervals[(str(inst),port)] = ival

  def has_interval(self,inst,port):
    return (str(inst),port) in self.intervals

  def get_interval(self,inst,port):
    if not self.has_interval(inst,port):
      raise Exception("no interval <%s,%s>" % (inst,port))
    return self.intervals[(str(inst),port)]

  def has_expr(self,inst,port):
    return (str(inst),port) in self.exprs

  def get_expr(self,inst,port):
    if not self.has_expr(inst,port):
      print(self.exprs)
      raise Exception("no expr <%s,%s>" % (inst,port))
    return self.exprs[(str(inst),port)]


  def set_expr(self,inst,port,expr):
    assert(isinstance(expr,genoplib.Op))
    self.exprs[(str(inst),port)] = expr

  def __repr__(self):
    st = ""
    for ((inst,port),ival) in self.intervals.items():
      if (inst,port) in self.exprs:
        expr = "(%s)" % self.exprs[(inst,port)]
      else:
        expr = ""

    st += "%s.%s = %s %s\n" % (inst,port,ival,expr)
    return st

class HardwareInfo:

  def __init__(self,dev, \
               scale_method=ScaleMethod.IDEAL,  \
               calib_obj=None, \
               one_mode=False, \
               no_scale=False):

    self.dev = dev
    self.scale_method = scale_method
    self.calib_obj = calib_obj
    self.mode_mappings = {}
    self.one_mode = one_mode
    self.quality_terms = {}
    for meas in QualityMeasure:
      self.quality_terms[meas] = []

  def get_quality_terms(self,qual):
    for term in self.quality_terms[qual]:
      yield term

  def add_quality_term(self,qual,term):
    assert(qual in self.quality_terms)
    self.quality_terms[qual].append(term)

  def register_modes(self,blk,modes):
    if self.one_mode and \
       any(map(lambda m: "h" in str(m), modes)):
      modes = list(filter(lambda m: not "h" in str(m), modes))
      print(modes)

    self.mode_mappings[blk.name] = modes

  def modes(self,blk_name):
    return self.mode_mappings[blk_name]

  def _get_port(self,instance,name):
    blk = self.dev.get_block(instance.block)
    if blk.inputs.has(name):
      return blk.inputs[name]
    elif blk.data.has(name):
      return blk.data[name]
    else:
      return blk.outputs[name]

  def get_board_frequency(self):
    return 1.0/self.dev.time_constant

  def get_freq_limit(self,instance,mode,port_name):
    assert(isinstance(port_name,str))
    port = self._get_port(instance,port_name)
    if hasattr(port,'freq_limit'):
      return port.freq_limit[mode]
    else:
      return None


  def get_noise(self,instance,mode,port_name):
    ZERO_NOISE = 1e-6
    assert(isinstance(port_name,str))
    port = self._get_port(instance,port_name)
    if not hasattr(port,'noise'):
      return ZERO_NOISE

    if port.noise is None:
      return ZERO_NOISE
    
    if not port.noise is None and \
       port.noise[mode] is None:
      print("[WARN] %s:%s has no noise in mode %s" % (instance,port_name,mode))
      return ZERO_NOISE

    return port.noise[mode]

  def get_quantize(self,instance,mode,port_name):
    assert(isinstance(port_name,str))
    port = self._get_port(instance,port_name)
    if port.quantize is None:
      return None

    return port.quantize[mode]

  def get_op_range(self,instance,mode,port_name):
    assert(isinstance(port_name,str))
    port = self._get_port(instance,port_name)
    ival = port.interval[mode]
    if ival is None:
      raise Exception("specification error: %s.%s has no operating range for mode %s" \
                      % (instance,port_name,mode))

    safe_ival = ival.scale(0.95)
    return safe_ival

  def get_empirical_relation(self,instance,mode,port):
    block = self.dev.get_block(instance.block)
    if self.scale_method == ScaleMethod.IDEAL or \
       not block.requires_calibration():
      return self.get_ideal_relation(instance,mode,port)
    else:
      out = block.outputs[port]
      delta = out.deltas[mode]
      cfg = adplib.BlockConfig(instance)
      cfg.modes = [mode]
      exp_models = exp_delta_model_lib.get_models(self.dev,  \
                                                 ['block','loc','output','static_config','calib_obj'],
                                                 block=block, \
                                                 loc=instance.loc, \
                                                 output=out, \
                                                 config=cfg, \
                                                 calib_obj=self.calib_obj)
      if len(exp_models) == 0:
        print("[[WARN]] no experimental model %s (%s)" \
              % (instance,mode))
        return None

      if not exp_models[0].complete:
        print(cfg)
        print(exp_models[0])
        raise Exception("experimental model must be complete")

      expr = delta.get_correctable_model(exp_models[0].params,low_level=False)
      return expr

  def get_ideal_relation(self,instance,mode,port):
    out = self.dev.get_block(instance.block) \
                  .outputs[port]
    assert(out.relation.has(mode))
    return out.relation[mode]

class SCVar:

  def __init__(self):
    pass

  def vars(self):
    return [self]

class QualityVar(SCVar):

  def __init__(self,name):
    SCVar.__init__(self)
    assert(isinstance(name,QualityMeasure))
    self.name = name


  def __repr__(self):
    return "quality(%s)" % self.name.value


class ModeVar(SCVar):

  def __init__(self,instance,modes):
    SCVar.__init__(self)
    self.inst = instance
    self.modes = modes

  def __repr__(self):
    return "mode(%s)" % self.inst

class InjectVar(SCVar):

  def __init__(self,inst,field,arg):
    SCVar.__init__(self)
    self.inst = inst
    self.field = field
    self.arg = arg


  def __repr__(self):
    return "inj(%s,%s,%s)" \
      % (self.inst,self.field,self.arg)




class FuncArgScaleVar(SCVar):

  def __init__(self,inst,datafield,arg):
    SCVar.__init__(self)
    self.inst = inst
    self.datafield = datafield
    self.arg = arg

  def __repr__(self):
    return "arg(%s,%s,%s)" \
      % (self.inst,self.datafield,self.arg)


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

  def __init__(self,instance,index):
    self.inst = instance
    self.index = index

  def __repr__(self):
    return "coeff(%s).%d" % (self.inst, \
                                self.index)

class PropertyVar(SCVar):
  class Type(Enum):
    MAXFREQ = "maxfreq"
    MINFREQ = "minfreq"
    INTERVAL_UPPER = "ivalU"
    INTERVAL_LOWER = "ivalL"
    QUANTIZE = "quantize"
    NOISE = "noise"

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

  def __len__(self):
    return len(self._terms)

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

  def exponentiate(self,expo):
    self._expos = list(map(lambda e: e*expo, self._expos))
    self._coeff = self._coeff**(expo)
    return self

  def product(self,mono):
    assert(isinstance(mono,SCMonomial))
    self.coeff *= mono.coeff
    for term,expo in mono.terms:
      self.add_term(term,expo)

  def add_term(self,term,expo=1.0):
    assert(isinstance(term,SCVar))
    assert(isinstance(expo,float) or isinstance(expo,int))
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



class SCLTE:

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
    return "%s <= %s" % (self.lhs,self.rhs)


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
    if self.subinterval.upper > 0 and \
       self.interval.upper <= 0:
      return False
    if self.subinterval.lower <= 0 and \
       self.interval.lower > 0:
      return False
    return True

  def trivial(self):
    assert(self.valid())
    if self.subinterval.is_value(0.0) and \
       self.interval.is_value(0.0):
      return True,True

    upper_trivial,lower_trivial = False,False
    if self.subinterval.upper <= 0 and \
       self.interval.upper >= 0:
      upper_trivial = True

    if self.subinterval.lower >= 0 and \
       self.interval.lower <= 0:
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
  def __init__(self,modevar,modes):
    assert(isinstance(modevar,ModeVar))
    for mode in modes:
      if not mode in modevar.modes:
        raise Exception("%s not a subset of %s" \
                        % (str(modes),str(all_modes)))
    self.mode_var = modevar
    self.valid_modes = list(modes)
    if len(self.valid_modes) == 0:
      raise Exception("no valid modes in %s" % str(modes))

  def vars(self):
    yield self.mode_var

  def __repr__(self):
    return "%s IN %s"  \
      % (self.mode_var,self.valid_modes)

class SCModeImplies:

  def __init__(self,modevar,mode,dep_var,value):
    assert(isinstance(modevar,ModeVar))
    assert(isinstance(value,float))
    assert(isinstance(dep_var,ConstCoeffVar) or \
           isinstance(dep_var,PropertyVar))
    self.mode_var = modevar
    self.mode = mode
    self.dep_var = dep_var
    self.value = value

  def vars(self):
    yield self.mode_var
    yield self.dep_var

  def __repr__(self):
    return "%s == %s :> %s = %s" % (self.mode_var,self.mode, \
                                    self.dep_var,self.value)

