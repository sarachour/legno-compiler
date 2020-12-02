from enum import Enum
import ops.interval as interval
import ops.generic_op as oplib
import ops.lambda_op as lambdoplib
import hwlib.exceptions as exceptions
import numpy as np
import util.util as util

class ExternalPins(Enum):
    NONE = "NONE"
    IN0_IN1 = "IN0_IN1"
    OUT0_OUT1 = "OUT0_OUT1"

class QuantizeType(Enum):
    LINEAR = "linear"

class Quantize:

    def __init__(self,n,interp_type,scale=1.0):
        assert(isinstance(n,int))
        assert(isinstance(interp_type,QuantizeType))
        self.n = n
        self.type = interp_type
        self.scale = scale

    def error(self,interval):
        assert(self.type == QuantizeType.LINEAR)
        val = float(interval.upper-interval.lower)/self.n
        assert(val > 0.0)
        return val

    def get_values(self,interval):
        if self.type == QuantizeType.LINEAR:
            return list(np.linspace(interval.lower,interval.upper,self.n))
        else:
            raise NotImplementedError

    def get_value(self,interval,code):
        vals = self.get_values(interval)
        return vals[code]

    def get_code(self,interval,value):
        vals = self.get_values(interval)
        eps = list(map(lambda v: abs(v-value), vals))
        idx = np.argmin(eps)
        return idx

    def round_value(self,interval,value):
        vals = self.get_values(interval)
        dist = list(map(lambda v: abs(v-value), vals))
        idx = np.argmin(dist)
        return vals[idx]

class BlockType(Enum):
    COMPUTE = "compute"
    ASSEMBLE = "assemble"
    ROUTE = "route"


class DeltaParamType(str,Enum):
  CORRECTABLE = 'correctable'
  LL_CORRECTABLE = "ll_correctable"
  GENERAL = 'general'

  def is_correctable(self,low_level=False):
      if self == DeltaParamType.GENERAL:
          return False
      elif self == DeltaParamType.LL_CORRECTABLE and not low_level:
          return False
      else:
          return True


class BlockDataType(str,Enum):
  CONST = 'const'
  EXPR = 'expr'

class BlockSignalType(Enum):
  ANALOG = 'analog'
  DIGITAL = 'digital'

class BlockStateType(Enum):
  CALIBRATE = "calib"
  CONNECTION = "conn"
  MODE = "mode"
  DATA = "data"
  CONSTANT = "const"

def msg_assert(clause,msg):
    if not clause:
        raise Exception(msg)

def interpret_enum(field,_enum_type):
    if isinstance(field,_enum_type):
        return field

    if isinstance(field,str):
        return _enum_type(field)

    return None

class BlockMode:

  def typecheck(self):
    for field,_type in zip(self._values,self._spec):
      if not isinstance(field,_type) and \
        (interpret_enum(field,_type) is None):
        return False
    return True


  def __init__(self,values,spec):
    self._values = values
    self._spec = spec
    self._is_array = False
    if isinstance(values,tuple) or \
       isinstance(values,list):
        self._is_array = True

    self.typecheck()

  def to_json(self):
    return {
        'values': self._values
    }

  @property
  def key(self):
    if self._is_array:
        return ",".join(map(lambda x: str(x),self._values))
    else:
        return self._values

  def __len__(self):
    if self._is_array:
        return len(self._values)
    else:
        return 1

  def equals(self,other_mode):
    if self._is_array != other_mode._is_array:
        return False

    if self._is_array:
      if len(self._values) != len(other_mode._values):
        return False
      for v1,v2 in zip(self._values,other_mode._values):
        if v1 != v2:
          return False
      return True
    else:
      return v1 == v2

  def match(self,pattern):
    assert(len(pattern) == len(self))
    for pat,mode,typ in zip(pattern,self._values,self._spec):
      pat_m = interpret_enum(mode,typ)
      if pat == '_':
        pat_e = None
      else:
        pat_e = interpret_enum(pat,typ)
      if pat_m != pat_e and pat_e != None:
          return False
    return True
  
  def __iter__(self):
    for v in self._values:
       yield v

  def __repr__(self):
    return "(%s)" % self.key

class BlockModeset:

  def __init__(self,type_spec):
    self._type = type_spec
    self._modes = {}
    self._order = []

  def matches(self,pattern):
    for mode in self:
      if mode.match(pattern):
        yield mode

  def get_by_key(self,key):
    return self._modes[key]

  def add(self,mode):
    mode_d = BlockMode(mode,self._type)
    assert(not mode_d.key in self._modes)
    self._modes[mode_d.key] = mode_d
    self._order.append(mode_d.key)

  def add_all(self,modes):
    for mode in modes:
      self.add(mode)

  def get(self,mode):
    bm = BlockMode(mode,self._type)
    for mode in self:
        if mode.equals(bm):
            return mode

    raise Exception("no mode exists")

  def __len__(self):
      return len(self._modes.keys())

  def __getitem__(self,m):
    if isinstance(m,int):
      return self._modes[self._order[m]]
    else:
      return self.get(m)

  def __iter__(self):
    for mode_key in self._order:
        yield self._modes[mode_key]

  def __repr__(self):
    return str(self._modes.values())

class BlockField:

  def __init__(self,name):
    self.name = name

  def initialize(self,blk):
      pass

class BlockFieldCollection:

  def __init__(self,block,block_t):
    self._block = block
    self._type = block_t
    self._collection = {}


  def singleton(self):
    assert(len(self) == 1)
    return list(self._collection.values())[0]

  def field_names(self):
    return list(self._collection.keys())

  def add(self,fld):
    assert(isinstance(fld,BlockField))
    assert(not fld.name in self._block.field_names())
    self._collection[fld.name] = fld
    fld.initialize(self._block)
    return fld

  def has(self,key):
    return key in self._collection

  def __getitem__(self,key):
    return self._collection[key]

  def __iter__(self):
    for v in self._collection.values():
      yield v

  def __len__(self):
      return len(self._collection.keys())

class BlockStateCollection(BlockFieldCollection):

    def __init__(self,block):
      BlockFieldCollection.__init__(self,block,BlockState)


    def lift(self,cfg,loc,data):
      blkcfg = cfg.configs.get(self._block.name,loc)
      blkcfg.modes = list(self._block.modes)

      for state in filter(lambda st: isinstance(st.impl, BCModeImpl), \
                          self):
        state.lift(cfg,self._block,loc,data)

      for state in filter(lambda st: not isinstance(st.impl, BCModeImpl), \
                          self):
        state.lift(cfg,self._block,loc,data)

    # turn this configuration into a low level spec
    def concretize(self,adp,loc):
      data = {}
      arrays = []
      for state in self:
        value = state.impl.apply(adp,self._block.name,loc)
        if state.array is None:
          assert(not state.variable in data)
          data[state.variable] = value
        else:
          if not state.variable in data:
            data[state.variable] = state.array.new_array()
            arrays.append(state.variable)

          idx = state.array.get_index(state.index)
          state.array.typecheck_value(value)
          data[state.variable][idx] = value

      return data



class ModeDependentProperty:

  def __init__(self,name,modeset,typ):
    self._fields = {}
    self._type = typ
    self.name = name
    self._modes = modeset
    for mode in self._modes:
        self._fields[mode.key] = None


  @property
  def value_type(self):
    return self._type

  def has(self,mode):
      return mode.key in self._fields

  def bind(self,mode_pattern,field):
    if not (isinstance(field,self._type)):
        raise Exception("field <%s> is not of type %s" \
                        % (field,self._type))

    for mode in self._modes.matches(mode_pattern):
        assert(self._fields[mode.key] is None)
        self._fields[mode.key] = field

  def __getitem__(self,mode):
    assert(isinstance(mode,BlockMode))
    return self._fields[mode.key]

  def get_by_property(self):
    props = {}
    for mode_key,prop in self._fields.items():
      if not prop in props:
        props[prop] = []
      props[prop].append(self._modes.get_by_key(mode_key))

    for prop,modes in props.items():
      if not prop is None:
        yield prop,modes

  def __repr__(self):
    st = ""
    for k,v in self._fields.items():
      if v is None:
        continue
      st += "%s->%s; " % (k,v)

    return st


class BCConstImpl:
  def __init__(self,state):
      self.state = state
      self.value = None

  def bind(self,value):
      self.state.valid(value)
      self.value = value

  def apply(self,adp,block_name,loc):
      if(self.value is None):
          raise Exception("unknown value for state <%s>" % self.state.name)
      return self.value

  def lift(self,adp,block,loc,data):
      self.state.valid(data)
      return

class BCModeImpl:
  def __init__(self,state):
      self.state = state
      self._bindings = []
      self._default = None

  def set_default(self,default):
      self.state.valid(value)
      self._default = default

  @property
  def default(self):
      self.state.valid(self._default)
      return self._default

  def bind(self,pattern,value):
      self.state.valid(value)
      self._bindings.append((pattern,value))

  def lift(self,adp,block,loc,data_value):
    cfg = adp.configs.get(block.name,loc)
    modes = []
    avail_modes = cfg.modes if not cfg.modes is None \
                  else block.modes

    for pat,value in self._bindings:
        casted_value = value.__class__(data_value)
        # this is the correct value
        if casted_value == value:
            for mode in avail_modes:
                if mode.match(pat):
                    modes.append(mode)

    assert(not modes is None)
    if not (len(modes) > 0):
        print("starting_modes: %s" % avail_modes)
        raise Exception("could not find modes for %s=%s" % (self.state.name, \
                                                            data_value))

    cfg.modes = modes

  def apply(self,adp,block_name,loc):
    cfg = adp.configs.get(block_name,loc)
    if cfg is None:
        raise exceptions.BlockInstFuncException(self,'apply', \
                                      block_name,loc, \
                                      "block config is none")
    if not cfg.complete():
        raise exceptions.BlockInstFuncException(self,'apply', \
                                      block_name,loc, \
                                      "block config is incomplete")

    values = []
    for pat,value in self._bindings:
        if cfg.mode.match(pat):
            values.append(value)

    if not (len(values) == 1):
        raise Exception("<%s> requires one unique value, found %s" \
                        % (self.state.name,values))
    return values[0]

class BCDataImpl:
  def __init__(self,state):
      self.state = state
      self.variable = None
      self.default = None

  def set_default(self,d):
      self.default = d

  def set_variable(self,v):
      self.variable =v

  def apply(self,adp,block_name,loc):
      assert(not self.variable is None)
      assert(not self.default is None)
      blkcfg = adp.configs.get(block_name,loc)
      stmt = blkcfg[self.variable]
      value = stmt.value*stmt.scf
      data_field = self.state.block.data[self.variable]
      interval = data_field.interval[blkcfg.mode]
      code = self.state.block.data[self.variable] \
                       .quantize[blkcfg.mode] \
                       .get_code(interval,value)
      return code

  def lift(self,adp,block,loc,data):
      blkcfg = adp.configs.get(block.name,loc)
      if not (blkcfg.complete()):
          print(blkcfg)
          raise Exception("configuration not complete!")

      data_field = self.state.block.data[self.variable]
      interval = data_field.interval[blkcfg.mode]
      value = block.data[self.variable] \
                       .quantize[blkcfg.mode] \
                       .get_value(interval,data)
      blkcfg.get(self.variable).value = value
      blkcfg.get(self.variable).scf = 1.0

class BCCalibImpl:
  def __init__(self,state):
      self.state = state
      self._default = None
      pass

  def set_default(self,default):
      assert(self.state.valid(default))
      self._default = default

  @property
  def default(self):
      if not (self.state.valid(self._default)):
          raise Exception("default value <%s> not valid for <%s>"  \
                          % (self._default,self.state.name))
      return self._default

  def apply(self,adp,block_name,loc):
    blkcfg = adp.configs.get(block_name,loc)
    if blkcfg.has(self.state.name):
        stmt = blkcfg[self.state.name]
        value = stmt.value
        if not (self.state.valid(value)):
            raise Exception("invalid value <%s> for state field <%s>" \
                            % (value,self.state.name))
    else:
        value = self.default


    return value

  def lift(self,adp,block,loc,data):
    blkcfg = adp.configs.get(block.name,loc)
    blkcfg.get(self.state.name).value = data


class BCConnImpl:
  def __init__(self,state):
      self.state = state
      self._incoming = []
      self._outgoing= []
      self._default = None

  def outgoing(self,source_port, \
               sink_block,sink_loc,sink_port,value):
      self.state.valid(value)
      assert(isinstance(source_port,str))

      data = (source_port,sink_block,sink_loc,sink_port,value)
      self._outgoing.append(data)

  def incoming(self,sink_port, \
             source_block,source_loc,source_port,value):
      self.state.valid(value)

      data = (sink_port,source_block, \
              source_loc,source_port,value)

      self._incoming.append(data)


  @property
  def default(self):
      assert(self.state.valid(self._default))
      return self._default

  def set_default(self,value):
      assert(self.state.valid(value))
      self._default = value

  def apply(self,adp,block_name,loc):
    for (source_port,sink_block,sink_loc,sink_port,value) in \
        self._outgoing:
        outgoing_conns = adp.outgoing_conns(block_name,loc,source_port)
        for conn in outgoing_conns:
            if conn.dest_match(sink_block,sink_loc,sink_port):
                return value

    for (sink_port,source_block,source_loc,source_port,value) in \
        self._incoming:
        incoming_conns = adp.incoming_conns(block_name,loc,sink_port)
        for conn in incoming_conns:
            if conn.source_match(source_block,source_loc,source_port):
                return value

    return self._default

  def lift(self,adp,block,loc,data):
    cfg = adp.configs.get(block.name,loc)
    #cfg.get(self.state.name).value = data

class BlockStateArray:

  def __init__(self,name,indices,values,length,default=None):
      self.name = name
      self.indices = indices

      self.length = length
      self.values = values
      assert(default in values)
      self.default = default

  def get_index(self,index):
      if isinstance(index,int):
          if not (index in self.indices):
              raise Exception("%s not in %s for <%s>" % (index,self.indices,self.name))
          return index
      else:
          enum_v = interpret_enum(index,self.indices)
          if not enum_v is None:
              return enum_v.code()
          else:
              raise Exception("cannot cast to index: <%s>" % enum_v)

  def new_array(self):
      return [self.default]*self.length

  def typecheck_value(self,v):
      return v in list(self.values)

class BlockState(BlockField):

  def __init__(self,name,state_type,values, \
               array=None, \
               index=None):
    BlockField.__init__(self,name)
    assert(hasattr(index,'code') or array is None)
    assert(isinstance(state_type, BlockStateType))
    self.type = state_type
    self.index = index
    self.array = array
    assert( (index is None and array is None) or \
            (not index is None and not array is None))
    self.values = list(values)
    self.variable = name if array is None else array.name
    if state_type == BlockStateType.CONNECTION:
        self.impl = BCConnImpl(self)
    elif state_type == BlockStateType.CALIBRATE:
        self.impl = BCCalibImpl(self)
    elif state_type == BlockStateType.CONSTANT:
        self.impl = BCConstImpl(self)
    elif state_type == BlockStateType.MODE:
        self.impl = BCModeImpl(self)
    elif state_type == BlockStateType.DATA:
        self.impl = BCDataImpl(self)
    else:
        raise NotImplementedError

  def initialize(self,block):
      self.block = block

  def valid(self,value):
      for v in self.values:
        if value == v:
          return True
      return False

  def nearest_value(self,value):
      return util.nearest_value(self.values,value)

  @property
  def min_value(self):
      return min(self.values)

  @property
  def max_value(self):
      return max(self.values)


  def lift(self,adp,block,loc,data):
    if not self.array is None:
        arr_idx = self.index.code()
        arr_name = self.array.name
        value = data[arr_name][arr_idx]
    else:
        value = data[self.name]

    self.impl.lift(adp,block,loc,value)

  def __str__(self):
    name = self.type.value
    name += " "
    name += self.variable
    if not self.index is None:
      name += "[%s]" % self.index.value
    name += " {\n"
    name += str(self.impl)
    name +="\n}"
    return name


class BlockInput(BlockField):

  def __init__(self,name,sig_type,ll_identifier):
      BlockField.__init__(self,name)
      assert(isinstance(sig_type, BlockSignalType))
      self.type = sig_type
      self.ll_identifier = ll_identifier

  def initialize(self,block):
      self.block = block
      self.interval = ModeDependentProperty("interval",block.modes,interval.Interval)
      self.freq_limit = ModeDependentProperty("max_frequency",block.modes, \
                                              float)
      self.noise = ModeDependentProperty("noise",block.modes,float)
      if self.type == BlockSignalType.DIGITAL:
          self.quantize = ModeDependentProperty("quantization", \
                                                block.modes, \
                                                Quantize)
      else:
          self.quantize = None

  @property
  def properties(self):
      yield self.interval
      yield self.freq_limit
      yield self.quantize

  def __repr__(self):
      indent = "  "
      st = "block-input %s : %s (%s) {\n" \
           % (self.name,self.type,self.ll_identifier.value);
      for prop in [self.interval,self.freq_limit,self.quantize]:
        if prop is None:
            continue

        text = str(prop)
        if text != "":
          st += "%s%s\n" % (indent,prop.name)
          st += "%s%s\n" % (indent+indent,text.replace(';','\n'+indent+indent))

      st += "}\n"
      return st


class PhysicalModelSpec:

    def __init__(self,relation,parameters,hidden_state):
        # sanity check
        all_vars = relation.vars()
        for v in all_vars:
           if not v in parameters and not v in hidden_state:
               raise Exception("variable <%s> is not a parameter or hidden code" % v)
        for v in parameters + hidden_state:
            if not v in all_vars:
                raise Exception("parameter or hidden state <%s> not in relation "% v)

        self.relation = relation
        self.params = parameters
        self.hidden_state = hidden_state

    @staticmethod
    def make(block,relation):
        all_hidden_vars = set(map(lambda st: st.name, \
                                filter(lambda st: isinstance(st.impl,BCCalibImpl), \
                                       block.state)))
        variables = set(relation.vars())
        hidden_state = list(variables.intersection(all_hidden_vars))
        model_pars = list(variables.difference(all_hidden_vars))
        return PhysicalModelSpec(relation,model_pars,hidden_state)

    def get_model(self,assigns):
        repls = dict(map(lambda tup: (tup[0],oplib.Const(tup[1])), \
                         params.items()))
        return self.relation.substitute(repls)

    def __repr__(self):
        return "{hidden-state:%s, params:%s, expr:%s}" % (self.hidden_state, \
                                                          self.params, \
                                                          self.relation)
class DeltaSpec:

    class Parameter:

        def __init__(self,name,typ,ideal_value,model=None):
            self.typ = typ
            self.name = name
            self.val = ideal_value
            assert(model is None \
                   or isinstance(model,PhysicalModelSpec))
            self._model = model

        @property
        def model(self):
            return self._model

        def __repr__(self):
            return "%s : %s = %s / model=%s" % (self.name, \
                                           self.typ.value, \
                                           self.val, \
                                           self._model)

    def __init__(self,rel,objective=None):
        assert(isinstance(rel,oplib.Op))
        self._params = {}
        self.relation = rel
        self._model_error = None
        self.objective = objective

    def get_params_of_type(self,typ):
        return list(filter(lambda p: p.typ == typ, \
                           self._params.values()))
 
    @property
    def model_error(self):
        return self._model_error

    @model_error.setter
    def model_error(self,v):
        self._model_error = v

    def get_model(self,params):
        repls = dict(map(lambda tup: (tup[0],oplib.Const(tup[1])), \
                         params.items()))
        return self.relation.substitute(repls)

    def get_correctable_model(self,params):
        pdict = dict(params)
        for par in params.keys():
            if not self._params[par].typ.is_correctable():
                pdict[par] = self._params[par].val

        return lambdoplib.simplify(self.get_model(pdict))

    @property
    def params(self):
        return list(self._params.keys())

    def param(self,param_name,param_type,ideal,model=None):
        assert(not param_name in self._params)
        self._params[param_name] = DeltaSpec.Parameter(param_name,\
                                                       param_type,\
                                                       ideal,\
                                                       model)


    def __getitem__(self,par):
        par_ = self._params[par]
        return par_

    def __repr__(self):
        st = "delta {\n"
        indent = "  "
        for par_name,par in self._params.items():
            st += "%spar %s\n" % (indent,par)

        st += "%srel %s\n" % (indent,self.relation)
        st += "}\n"
        return st

class BlockOutput(BlockField):

  def __init__(self,name,sig_type,ll_identifier):
    BlockField.__init__(self,name)
    assert(isinstance(sig_type, BlockSignalType))
    self.type = sig_type
    self.ll_identifier = ll_identifier

  def initialize(self,block):
    self.block = block
    self.interval = ModeDependentProperty("interval",block.modes,interval.Interval)
    self.noise = ModeDependentProperty("noise",block.modes,float)
    self.freq_limit = ModeDependentProperty("max_frequency",block.modes,float)
    self.relation = ModeDependentProperty("relation",block.modes,oplib.Op)
    self.deltas = ModeDependentProperty("delta_model",block.modes,DeltaSpec)
    if self.type == BlockSignalType.DIGITAL:
      self.quantize = ModeDependentProperty("quantization", \
                                            block.modes, \
                                            Quantize)
    else:
      self.quantize = None

  @property
  def properties(self):
    yield self.interval
    yield self.freq_limit
    yield self.quantize
    yield self.freq_limit
    yield self.delta_spec
    yield self.relation

class BlockData(BlockField):

  def __init__(self,name,data_type,inputs=[]):
    BlockField.__init__(self,name)
    assert(isinstance(data_type, BlockDataType))
    self.type = data_type
    self.n_inputs = len(inputs)
    self.inputs = inputs

  def initialize(self,block):
    self.block = block
    if self.type == BlockDataType.CONST:
      self.quantize = ModeDependentProperty("quantization", \
                                            block.modes, \
                                            Quantize)

      self.interval = ModeDependentProperty("interval", \
                                            block.modes, \
                                            interval.Interval)


    else:
      assert(isinstance(self.n_inputs,int))
      print("[WARN] need to add quantization info")

  def round_value(self,mode,value):
      ival = self.interval[mode]
      quant = self.quantize[mode]
      return quant.round_value(ival,value)


  def __repr__(self):
      return "data %s type=%s inputs=%s" % (self.name,self.type,self.inputs)

class Block:

  def __init__(self,name,typ,mode_spec):
    self.inputs = BlockFieldCollection(self,BlockInput)
    self.outputs = BlockFieldCollection(self,BlockOutput)
    self.data = BlockFieldCollection(self,BlockData)
    self.state = BlockStateCollection(self)
    self.modes = BlockModeset(mode_spec)

    self.name = name
    self.ll_name = name
    self.type = typ

  def requires_calibration(self):
      for _ in filter(lambda st : isinstance(st.impl,BCCalibImpl) , \
                    self.state):
          return True
      return False


  def port(self,name):
    if self.inputs.has(name):
      return self.inputs[name]
    if self.outputs.has(name):
      return self.outputs[name]
    raise Exception("unknown port: %s" % name)

  def field_collections(self):
    yield self.inputs
    yield self.outputs
    yield self.data
    yield self.state

  def field_names(self):
    names = []
    for coll in self.field_collections():
      names += coll.field_names()

    return names

  def add_mode(self,mode):
    self.modes.append(mode)
    for coll in self.field_collections():
      coll.add_mode(mode)
