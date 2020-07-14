from enum import Enum
import ops.interval as interval
import ops.generic_op as oplib
import hwlib.exceptions as exceptions
import numpy as np

class QuantizeType(Enum):
    LINEAR = "linear"

class Quantize:

    def __init__(self,n,interp_type):
        assert(isinstance(n,int))
        assert(isinstance(interp_type,QuantizeType))
        self.n = n
        self.type = interp_type

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

class BlockType(Enum):
    COMPUTE = "compute"
    ASSEMBLE = "assemble"
    ROUTE = "route"


class DeltaParamType(str,Enum):
  CORRECTABLE = 'correctable'
  GENERAL = 'general'


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

  def __repr__(self):
    return "(%s)" % self.key

class BlockModeset:

  def __init__(self,type_spec):
    self._type = type_spec
    self._modes = {}

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
      return self.get(m)

  def __iter__(self):
    for mode in self._modes.values():
      yield mode

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
      for state in self:
        state.lift(cfg,self._block,loc,data)

    # turn this configuration into a low level spec
    def concretize(self,cfg,loc):
      data = {}
      arrays = []
      for state in self:
        value = state.impl.apply(cfg,self._block.name,loc)
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
    assert(isinstance(field,self._type))
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
      assert(blkcfg.complete())
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
        assert(self.state.valid(value))
    else:
        value = self.default


    return value

  def lift(self,adp,block,loc,data):
    blkcfg = adp.configs.get(block.name,loc)
    blkcfg.get(self.state.name).value = data


class BCConnImpl:
  def __init__(self,state):
      self.state = state
      self._sources= {}
      self._sinks= {}
      self._default = None

  def sink(self,source_port,block,sink,value):
      self.state.valid(value)
      if not source_port in self._sinks:
          self._sinks[source_port] = []

      self._sinks[source_port].append((block,sink,value))

  def source(self,block,source,sink_port,value):
      self.state.valid(value)
      if not sink_port in self._sources:
          self._sources[sink_port] = []

      self._sources[sink_port].append((block,source,value))


  @property
  def default(self):
      assert(self.state.valid(self._default))
      return self._default

  def set_default(self,value):
      assert(self.state.valid(value))
      self._default = value

  def apply(self,adp,block_name,loc):
    '''
    sink_conns = adp.conns.incoming(block_name,loc)
    for src_loc,sink_loc in sink_conns:
        pass
    source_conns = adp.conns.outgoing(block_name,loc)
    for src_loc,sink_loc in sink_conns:
        pass
    '''
    print("TODO: actually apply connection impl")
    return self._default

  def lift(self,adp,block,loc,data):
    cfg = adp.configs.get(block.name,loc)
    print("TODO: actually apply connection impl")
    return self._default

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

  # add the 
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
      self.freq_limit = ModeDependentProperty("max_frequency",block.modes,float)
      self.quantize = ModeDependentProperty("quantization",block.modes,list)

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
        text = str(prop)
        if text != "":
          st += "%s%s\n" % (indent,prop.name)
          st += "%s%s\n" % (indent+indent,text.replace(';','\n'+indent+indent))

      st += "}\n"
      return st


class DeltaSpec:

    def __init__(self,rel):
        assert(isinstance(rel,oplib.Op))
        self.relation = rel
        self._params = {}
        self.ideal_values = {}

    def get_model(self,params):
        repls = dict(map(lambda tup: (tup[0],oplib.Const(tup[1])), \
                         params.items()))
        return self.relation.substitute(repls)

    def get_correctable_model(self,params):
        pdict = dict(params)
        for par in params.keys():
            if self._params[par]  \
               != DeltaParamType.CORRECTABLE:
                pdict[par] = self.ideal_values[par]

        return self.get_model(pdict)

    @property
    def params(self):
        return list(self._params.keys())

    def param(self,param_name,param_type,ideal):
        assert(not param_name in self._params)
        self._params[param_name] = param_type
        self.ideal_values[param_name] = ideal

    def __getitem__(self,par):
        type_ = self._params[par]
        val = self.ideal_values[par]
        return type_,val

    def __repr__(self):
        st = "delta {\n"
        indent = "  "
        for par_name,typ_ in self._params.items():
            val = self.ideal_values[par_name]
            st += "%spar %s: %s = %s\n" % (indent,par_name,typ_,val)
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
    self.freq_limit = ModeDependentProperty("max_frequency",block.modes,float)
    self.relation = ModeDependentProperty("relation",block.modes,oplib.Op)
    self.deltas = ModeDependentProperty("delta_model",block.modes,DeltaSpec)
    if self.type == BlockSignalType.DIGITAL:
      self.quantize = ModeDependentProperty("quantization",block.modes,Quantize)

  @property
  def properties(self):
    yield self.interval
    yield self.freq_limit
    yield self.quantize
    yield self.freq_limit
    yield self.delta_spec
    yield self.relation

class BlockData(BlockField):

  def __init__(self,name,data_type,inputs=None):
    BlockField.__init__(self,name)
    assert(isinstance(data_type, BlockDataType))
    self.type = data_type
    self.n_inputs = inputs
    if not inputs is None:
        self.args = list(map(lambda i: "x%d" % i, \
                             range(inputs)))

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

class Block:

  def __init__(self,name,typ,mode_spec):
    self.inputs = BlockFieldCollection(self,BlockInput)
    self.outputs = BlockFieldCollection(self,BlockOutput)
    self.data = BlockFieldCollection(self,BlockData)
    self.state = BlockStateCollection(self)
    self.modes = BlockModeset(mode_spec)

    self.name = name
    self.type = typ

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
