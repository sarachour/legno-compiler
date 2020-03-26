from enum import Enum
import ops.interval as interval
import ops.generic_op as oplib
import hwlib2.exceptions as exceptions

class QuantizeType(Enum):
    LINEAR = "linear"

class Quantize:

    def __init__(self,n,interp_type):
        assert(isinstance(n,int))
        assert(isinstance(interp_type,QuantizeType))
        self.n = n
        self.type = interp_type

class BlockType(Enum):
    COMPUTE = "compute"
    COPY = "copy"
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

class BlockCodeType(Enum):
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

  def __init__(self,values,spec):
    self._values = values
    self._spec = spec

class BlockModeset:

  def __init__(self,type_spec):
    self._type = type_spec
    self._modes = []

  def typecheck(self,mode):
    for field,_type in zip(mode,self._type):
      if not isinstance(field,_type) and \
        (interpret_enum(field,_type) is None):
        print(field,_type)
        return False
    return True

  def match(self,pattern,mode):
    assert(len(pattern) == len(mode))
    assert(len(self._type) == len(mode))
    for pat,mode,typ in zip(pattern,mode,self._type):
      pat_m = interpret_enum(mode,typ)
      if pat == '_':
        pat_e = None
      else:
        pat_e = interpret_enum(pat,typ)
      if pat_m != pat_e and pat_e != None:
          return False
    return True

  def matches(self,pattern):
      for mode in self:
        if self.match(pattern,mode):
          yield mode

  def add(self,mode):
      assert(not mode in self._modes)
      msg_assert(self.typecheck(mode), \
                 '%s not of type %s' % (mode,self._type))

  def add_all(self,modes):
    for mode in modes:
      self.add(mode)

  def __iter__(self):
    for mode in self._modes:
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

  def __getitem__(self,key):
    return self._collection[key]

  def __iter__(self):
    for v in self._collection.values():
      yield v

class BlockCodeCollection(BlockFieldCollection):

    def __init__(self,block):
      BlockFieldCollection.__init__(self,block,BlockCode)

    # turn this configuration into a low level spec
    def concretize(self,cfg,loc):
      data = {}
      arrays = []
      for code in self:
        value = code.impl.apply(cfg,self._block.name,loc)
        if code.array is None:
          assert(not code.variable in data)
          data[code.variable] = value
        else:
          if not code.variable in data:
            data[code.variable] = [code.array.default] \
                                  *code.array.length
            arrays.append(code.variable)

          assert(not code.index in data[code.variable])
          data[code.variable][code.index.to_code()] = value

      return data



class ModeDependentProperty:

  def __init__(self,modeset,typ):
    self._fields = {}
    self._type = typ
    self._modes = modeset

  def declare(self,mode):
    self._fields[mode] = None

 

  def bind(self,mode_pattern,field):
    assert(isinstance(field,self._type))
    for mode in self._modes.matches(mode_pattern):
        assert(self._fields[mode] is None)
        self._fields[mode] = field

class BCConstImpl:
  def __init__(self,code):
      self.code = code
      self.value = None

  def bind(self,value):
      self.code.valid(value)
      self.value = value

  def apply(self,adp,block_name,loc):
      assert(not self.value is None)
      return self.value

class BCModeImpl:
  def __init__(self,code):
      self.code = code
      self._bindings = []
      self._default = None

  def set_default(self,default):
      self.code.valid(value)
      self._default = default

  @property
  def default(self):
      self.code.valid(self._default)
      return self._default

  def bind(self,pattern,value):
      self.code.valid(value)
      self._bindings.append((pattern,value))

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

    mode = cfg.mode
    modeset = self.code.block.modes
    values = []
    for pat,value in self._bindings:
        if modeset.match(pat,mode):
            values.append(value)

    assert(len(values) == 1)
    return values[0]

class BCDataImpl:
  def __init__(self,code):
      self.code = code
      pass

class BCCalibImpl:
  def __init__(self,code):
      self.code = code
      self._default = None
      pass

  def set_default(self,default):
      assert(self.code.valid(default))
      self._default = default

  @property
  def default(self):
      assert(self.code.valid(self._default))
      return self._default

  def apply(self,adp,block_name,loc):
      print("[BCCalibImpl.apply] not implemented")
      return self.default

class BCConnImpl:
  def __init__(self,code):
      self.code = code
      self._sources= {}
      self._sinks= {}
      self._default = None

  def sink(self,source_port,block,sink,value):
      self.code.valid(value)
      if not source_port in self._sinks:
          self._sinks[source_port] = []

      self._sinks[source_port].append((block,sink,value))

  def source(self,block,source,sink_port,value):
      self.code.valid(value)
      if not sink_port in self._sources:
          self._sources[sink_port] = []

      self._sources[sink_port].append((block,source,value))


  @property
  def default(self):
      assert(self.code.valid(self._default))
      return self._default

  def set_default(self,value):
      assert(self.code.valid(value))
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
      return self._default

class BlockCodeArray:

  def __init__(self,name,indices,values,length,default=None):
      self.name = name
      self.indices = indices
      self.values = values
      self.length = length
      assert(default in values)
      self.default = default

class BlockCode(BlockField):

  def __init__(self,name,code_type,values, \
               array=None, \
               index=None):
    BlockField.__init__(self,name)
    assert(isinstance(code_type, BlockCodeType))
    self.type = code_type
    self.index = index
    self.array = array
    assert( (index is None and array is None) or \
            (not index is None and not array is None))
    self.values = values
    self.variable = name if array is None else array.name
    if code_type == BlockCodeType.CONNECTION:
        self.impl = BCConnImpl(self)
    elif code_type == BlockCodeType.CALIBRATE:
        self.impl = BCCalibImpl(self)
    elif code_type == BlockCodeType.CONSTANT:
        self.impl = BCConstImpl(self)
    elif code_type == BlockCodeType.MODE:
        self.impl = BCModeImpl(self)
    elif code_type == BlockCodeType.DATA:
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

  def __init__(self,name,sig_type):
      BlockField.__init__(self,name)
      assert(isinstance(sig_type, BlockSignalType))
      self.type = sig_type

  def initialize(self,block):
      self.block = block
      self.interval = ModeDependentProperty(block.modes,interval.Interval)
      self.freq_limit = ModeDependentProperty(block.modes,float)
      self.quantize = ModeDependentProperty(block.modes,list)

  @property
  def properties(self):
      yield self.interval
      yield self.freq_limit
      yield self.quantize

class DeltaSpec:

    def __init__(self,rel):
        assert(isinstance(rel,oplib.Op))
        self.relation = rel
        self.params = {}
        self.ideal_values = {}

    def param(self,param_name,param_type,ideal):
        assert(not param_name in self.params)
        self.params[param_name] = param_type
        self.ideal_values[param_name] = ideal

class BlockOutput(BlockField):

  def __init__(self,name,sig_type):
    BlockField.__init__(self,name)
    assert(isinstance(sig_type, BlockSignalType))
    self.type = sig_type


  def initialize(self,block):
    self.block = block
    self.interval = ModeDependentProperty(block.modes,interval.Interval)
    self.freq_limit = ModeDependentProperty(block.modes,float)
    self.relation = ModeDependentProperty(block.modes,oplib.Op)
    self.deltas = ModeDependentProperty(block.modes,DeltaSpec)
    if self.type == BlockSignalType.DIGITAL:
      self.quantize = ModeDependentProperty(block.modes,list)

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
      self.quantize = ModeDependentProperty(block.modes, \
                                            Quantize)
    else:
      assert(isinstance(self.n_inputs,int))

    self.interval = ModeDependentProperty(block.modes, \
                                          interval.Interval)


class Block:

  def __init__(self,name,typ,mode_spec):
    self.inputs = BlockFieldCollection(self,BlockInput)
    self.outputs = BlockFieldCollection(self,BlockOutput)
    self.data = BlockFieldCollection(self,BlockData)
    self.codes = BlockCodeCollection(self)
    self.modes = BlockModeset(mode_spec)

    self._name = name
    self._type = typ

  @property
  def name(self):
    return self._name

  def field_collections(self):
    yield self.inputs
    yield self.outputs
    yield self.data
    yield self.codes

  def field_names(self):
    names = []
    for coll in self.field_collections():
      names += coll.field_names()

    return names

  def add_mode(self,mode):
    self.modes.append(mode)
    for coll in self.field_collections():
      coll.add_mode(mode)
