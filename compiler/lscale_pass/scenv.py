from enum import Enum
import sys
import numpy as np
import util.util as util
import util.config as CONFIG
import hwlib.model as hwmodel
import compiler.lscale_pass.lscale_util as lscale_util

class LScaleVarType(Enum):
  SCALE_VAR= "SCV"
  GAIN_VAR = "GNV"

  OP_RANGE_VAR = "OPV"
  INJECT_VAR = "IJV"
  VAR = "VAR"
  MODE_VAR = "MODV"
  TAU = "TAU"
  PHYS_OPRANGE_SCALE_VAR_UPPER = "pOPu"
  PHYS_OPRANGE_SCALE_VAR_LOWER = "pOPl"
  PHYS_GAIN_VAR = "pGNV"
  PHYS_UNCERTAINTY = "pUNC"



class LScaleEnvParams:

  def __init__(self, \
               model,\
               mdpe, \
               mape, \
               vmape, \
               mc, \
               max_freq_khz=None):
    self.mdpe = mdpe
    self.mape = mape
    self.vmape = vmape
    self.mc = mc

    self.max_freq_hz = None
    if not max_freq_khz is None:
      self.max_freq_hz = max_freq_khz*1000.0

    self.set_model(model)

  def ideal(self):
    self.model = util.DeltaModel.IDEAL
    self.propagate_uncertainty = False
    self.enable_quantize_constraint = False
    self.enable_quality_constraint = False
    self.enable_bandwidth_constraint = True
    self.only_scale_modes_with_models = False


  def delta(self,model):
    self.model = model
    self.propagate_uncertainty = False
    self.enable_quantize_constraint = True
    self.enable_quality_constraint = True
    self.enable_bandwidth_constraint = True
    self.only_scale_modes_with_models = True

  def naive(self,model):
    self.model = model
    self.propagate_uncertainty = False
    self.enable_quantize_constraint = True
    self.enable_quality_constraint = True
    self.enable_bandwidth_constraint = True
    self.only_scale_modes_with_models = False


  def set_model(self,model):
    if model == util.DeltaModel.IDEAL:
      self.ideal()
    elif model.uses_delta_model():
      self.delta(model)
    else:
      self.naive(model)

    self.calib_obj = self.model.calibrate_objective()

  def tag(self):
    return util.pack_model(
      model=self.model,
      mdpe=self.mdpe,
      mape=self.mape,
      vmape=self.vmape,
      mc=self.mc,
      bandwidth_hz=self.max_freq_hz
    )

class LScaleEnv:
  def __init__(self, \
               model, \
               mdpe, \
               mape, \
               vmape, \
               mc, \
               max_freq_khz=None):
    # scaling factor name to port
    self._to_lscale_var = {}
    self._from_lscale_var ={}

    self._in_use = {}

    self.params = LScaleEnvParams(model,
                                  mdpe=mdpe, \
                                  mape=mape, \
                                  mc=mc, \
                                  vmape=vmape, \
                                  max_freq_khz=max_freq_khz)
    self.model_db = hwmodel.ModelDB(self.params.calib_obj)
    self._eqs = []
    self._ltes = []
    self._failed = False
    self._failures = []

    self._use_tau = False
    self._solved = False
    self._interactive = False
    self.decl_lscale_var((),LScaleVarType.TAU)

    self.time_scaling = True

  def set_time_scaling(self,v):
    self.time_scaling = v

  def tau(self):
    return self.to_lscale_var(LScaleVarType.TAU,())

  def interactive(self):
    self._interactive = True

  def set_solved(self,solved_problem):
      self._solved = solved_problem

  def solved(self):
      return self._solved

  def use_tau(self):
      self._in_use[self.tau()] = True

  def uses_tau(self):
    return self._in_use[self.tau()]

  def fail(self,msg):
      self._failed = True
      self._failures.append(msg)

  def failures(self):
    return self._failures

  def failed(self):
      return self._failed

  def in_use(self,tup,tag=LScaleVarType.VAR):
    var_name = self.to_lscale_var(tag,tup)
    return self._in_use[var_name]


  def lscale_var_in_use(self,var_name):
    return self._in_use[var_name]

  def variables(self,in_use=False):
    for var in self._from_lscale_var.keys():
      if self.lscale_var_in_use(var) or not in_use:
        yield var

  def eqs(self):
    for lhs,rhs,annot in self._eqs:
      yield (lhs,rhs,annot)

  def ltes(self):
    for lhs,rhs,annot in self._ltes:
      yield (lhs,rhs,annot)

  def get_lscale_var_info(self,scvar_var):
    if not scvar_var in self._from_lscale_var:
      print(self._from_lscale_var.keys())
      raise Exception("not scaling factor table in <%s>" % scvar_var)

    result = self._from_lscale_var[scvar_var]
    return result

  def get_tag(self,var):
    result = self.get_lscale_var_info(var)
    return result[0]

  def lscale_vars(self):
    return self._from_lscale_var.keys()

  def has_lscale_var(self,tup, tag=LScaleVarType.VAR):
    varname = self.to_lscale_var(tag,tup)
    return varname in self._from_lscale_var

  def get_lscale_var(self,tup, tag=LScaleVarType.VAR):
    varname = self.to_lscale_var(tag,tup)

    if not varname in self._from_lscale_var:
      for p in self._from_lscale_var.keys():
        print("  var: %s" % p)
      raise Exception("error: cannot find <%s> in var dict" % str(varname))

    self._in_use[varname] = True
    return varname

  def to_lscale_var(self,tag,tup):
    args = [tag.value] + list(tup)
    return "_".join(map(lambda a: str(a), args))

  def decl_lscale_var(self,tup, \
                     tag=LScaleVarType.VAR):
      # create a scaling factor from the variable name
    var_name = self.to_lscale_var(tag,tup)
    if var_name in self._from_lscale_var:
      return var_name

    self._from_lscale_var[var_name] = (tag,tup)
    self._to_lscale_var[(tag,tup)] = var_name
    self._in_use[var_name] = False
    return var_name

  def get_inject_var(self,block_name,loc,port,handle=None):
    return self.get_lscale_var((block_name,loc,port,handle), \
                               tag=LScaleVarType.INJECT_VAR)

  def decl_inject_var(self,block_name,loc,port,handle=None):
    return self.decl_lscale_var((block_name,loc,port,handle), \
                               tag=LScaleVarType.INJECT_VAR)

  def has_inject_var(self,block_name,loc,port,handle=None):
    var_name =self.to_lscale_var(LScaleVarType.INJECT_VAR,
                                (block_name,loc,port,handle))
    return var_name in self._from_lscale_var

  def get_scvar(self,block_name,loc,port,handle=None):
    return self.get_lscale_var((block_name,loc,port,handle), \
                              tag=LScaleVarType.SCALE_VAR)

  def decl_scvar(self,block_name,loc,port,handle=None):
    return self.decl_lscale_var((block_name,loc,port,handle), \
                              tag=LScaleVarType.SCALE_VAR)


  def get_scvar(self,block_name,loc,port,handle=None):
    return self.get_lscale_var((block_name,loc,port,handle), \
                              tag=LScaleVarType.SCALE_VAR)



  def eq(self,v1,v2,annot):
      lscale_util.log_debug("%s == %s {%s}" % (v1,v2,annot))
      # TODO: equality
      if self._interactive:
        input()
      succ,lhs,rhs = lscale_util.cancel_signs(v1,v2)
      if not succ:
        self.fail("could not cancel signs: %s == %s" % (v1,v2))
      self._eqs.append((lhs,rhs,annot))


  def lte(self,v1,v2,annot):
    lscale_util.log_debug("%s <= %s {%s}" % (v1,v2,annot))

    c1,_ = v1.factor_const()
    c2,_ = v2.factor_const()
    if c1 == 0 and c2 >= 0:
      return
    if c2 == 0 and c1 > 0:
      self.fail("trivially false: %s <= %s" % (v1,v2))

    # TODO: equality
    if self._interactive:
      input()
    self._ltes.append((v1,v2,annot))

  def gte(self,v1,v2,annot):
      # TODO: equality
      self.lte(v2,v1,annot)

class LScaleInferEnv(LScaleEnv):

    def __init__(self,model, \
                 mdpe, \
                 mape, \
                 vmape, \
                 mc, \
                 max_freq_khz=None):
      LScaleEnv.__init__(self,model, \
                         max_freq_khz=max_freq_khz, \
                         mdpe=mdpe,
                         mape=mape,
                         vmape=vmape,
                         mc=mc)
      self._exactly_one = []
      self._implies = {}
      self._lts = []

    def decl_op_range_var(self,block_name,loc,port,handle=None):
      return self.decl_lscale_var((block_name,loc,port,handle),
                                 tag=LScaleVarType.OP_RANGE_VAR)

    def decl_gain_var(self,block_name,loc,port,handle=None):
      return self.decl_lscale_var((block_name,loc,port,handle),
                                 tag=LScaleVarType.GAIN_VAR)

    def get_gain_var(self,block_name,loc,port,handle=None):
      return self.get_lscale_var((block_name,loc,port,handle),
                                tag=LScaleVarType.GAIN_VAR)

    def get_op_range_var(self,block_name,loc,port,handle=None):
      return self.get_lscale_var((block_name,loc,port,handle),
                                tag=LScaleVarType.OP_RANGE_VAR)

    def has_op_range_var(self,block_name,loc,port,handle=None):
      return self.has_lscale_var((block_name,loc,port,handle),
                                tag=LScaleVarType.OP_RANGE_VAR)


    def decl_mode_var(self,block_name,loc,mode):
      return self.decl_lscale_var((block_name,loc,mode),
                          tag=LScaleVarType.MODE_VAR)


    def get_mode_var(self,block_name,loc,mode):
      return self.get_lscale_var((block_name,loc,mode),
                                tag=LScaleVarType.MODE_VAR)

    def has_mode_var(self,block_name,loc,mode):
      return self.has_lscale_var((block_name,loc,mode),
                                tag=LScaleVarType.MODE_VAR)


    def decl_phys_op_range_scvar(self,block_name,loc,port,handle=None,lower=True):
      if lower:
        return self.decl_lscale_var((block_name,loc,port,handle), \
                                   tag=LScaleVarType.PHYS_OPRANGE_SCALE_VAR_LOWER)
      else:
        return self.decl_lscale_var((block_name,loc,port,handle), \
                                   tag=LScaleVarType.PHYS_OPRANGE_SCALE_VAR_UPPER)

    def decl_phys_gain_var(self,block_name,loc,port,handle=None):
      return self.decl_lscale_var((block_name,loc,port,handle), \
                                 tag=LScaleVarType.PHYS_GAIN_VAR)

    def decl_phys_uncertainty(self,block_name,loc,port,handle=None):
      return self.decl_lscale_var((block_name,loc,port,handle), \
                                 tag=LScaleVarType.PHYS_UNCERTAINTY)

    def get_phys_op_range_scvar(self,block_name,loc,port,handle=None,lower=True):
      if lower:
        return self.get_lscale_var((block_name,loc,port,handle), \
                                  tag=LScaleVarType.PHYS_OPRANGE_SCALE_VAR_LOWER)
      else:
        return self.get_lscale_var((block_name,loc,port,handle), \
                                  tag=LScaleVarType.PHYS_OPRANGE_SCALE_VAR_UPPER)



    def get_phys_gain_var(self,block_name,loc,port,handle=None):
      return self.get_lscale_var((block_name,loc,port,handle), \
                                tag=LScaleVarType.PHYS_GAIN_VAR)

    def get_phys_uncertainty(self,block_name,loc,port,handle=None):
      return self.get_lscale_var((block_name,loc,port,handle), \
                                tag=LScaleVarType.PHYS_UNCERTAINTY)


    def implies(self,condvar,var,value):
      assert(condvar in self._from_lscale_var)
      if not condvar in self._implies:
        self._implies[condvar] = []
      lscale_util.log_info("%s -> %s = %s" % (condvar,var,value))
      self._implies[condvar].append((var,value))

    def exactly_one(self,exclusive):
      if len(exclusive) == 0:
        return

      for v in exclusive:
        assert(v in self._from_lscale_var)
      self._exactly_one.append(exclusive)

    def get_lts(self):
      for lhs,rhs,annot in self._lts:
        yield lhs,rhs,annot

    def get_implies(self):
      for condvar in self._implies:
        for var2,value in self._implies[condvar]:
          yield condvar,var2,value

    def get_exactly_one(self):
      for exclusive in self._exactly_one:
        yield exclusive


    def lt(self,v1,v2,annot):
      lscale_util.log_debug("%s < %s {%s}" % (v1,v2,annot))
      self._lts.append((v1,v2,annot))

    def gt(self,v1,v2,annot):
      # TODO: equality
      self.lt(v2,v1,annot)

