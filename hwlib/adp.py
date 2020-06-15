import hwlib.block as blocklib
import hwlib.device as devlib
from enum import Enum

class BlockInst:

  def __init__(self,name,loc):
    assert(isinstance(name,str))
    assert(isinstance(loc,devlib.Location))
    self.block = name
    self.loc = loc

  def to_json(self):
    return {
      'block': self.block,
      'loc': self.loc.to_json()
    }

  def __repr__(self):
    return "%s.%s" % (self.block,self.loc)

class BlockInstanceCollection:

  def __init__(self,adp):
    self._adp = adp
    self._collection = {}


  def configs(self,block=None):
    assert(block is None or isinstance(block,str))
    if block is None:
      for blk,insts in self._collection.items():
        for inst,cfg in insts.items():
          yield data

    else:
      if not block in self._collection:
        return

      for inst,cfg in self._collection[block]:
        yield data

  def has(self,blockname,loc):
    assert(isinstance(blockname,str))
    if not blockname in self._collection:
      return False
    if not loc in self._collection[blockname]:
      return False
    return True

  def get(self,blockname,loc):
    assert(self.has(blockname,loc))
    return self._collection[blockname][loc]

  def add(self,data):
    assert(hasattr(data,'inst') and
           isinstance(data.inst,BlockInst))
    if not data.inst.block in self._collection:
      self._collection[data.inst.block] = {}

    assert(not str(data.inst.loc) \
           in self._collection[data.inst.block])
    self._collection[data.inst.block][data.inst.loc] = data

  def __getitem__(self,key):
    return self._collection[key]


class ConfigStmtType(Enum):
  STATE = "state"
  CONSTANT = "const"
  PORT = "port"

class ConfigStmt:

  def __init__(self,type_,name):
    self.name = name
    assert(isinstance(type_,ConfigStmtType))
    self.t = type_

  def pretty_print(self):
    raise NotImplementedError()

  def to_json(self):
    raise NotImplementedError

  def __repr__(self):
    return "%s %s %s" % (self.name,self.t.value,self.pretty_print())

class ConstDataConfig(ConfigStmt):

  def __init__(self,field,value):
    ConfigStmt.__init__(self,ConfigStmtType.CONSTANT,field)
    self.value = value
    self.scf = 1.0

  def pretty_print(self):
    return "val=%f scf=%f" \
      % (self.value,self.scf)

  def to_json(self):
    return {
      'name':self.name,
      'type': self.t.value,
      'scf': self.scf,
      'value': self.value
    }

class ExprDataConfig(ConfigStmt):

  def __init__(self,field,args,expr):
    ConfigStmt.__init__(self,ConfigStmtType.EXPR,field)
    self.args = args
    self.scfs = {}
    self.injs = {}
    self.expr = expr
    for key in args + [field]:
      self.scfs[key] = 1.0
      self.injs[key] = 1.0



class PortDataConfig(ConfigStmt):

  def __init__(self,name):
    ConfigStmt.__init__(self,ConfigStmtType.PORT,name)
    self.scf = 1.0

  def pretty_print(self):
    return "scf=%f" % (self.scf)

  def to_json(self):
    return {
      'name':self.name,
      'type': self.t.value,
      'scf': self.scf
    }

class StateConfig(ConfigStmt):

  def __init__(self,name,value):
    ConfigStmt.__init__(self,ConfigStmtType.STATE,name)
    self.name = name
    self.value = value

  def pretty_print(self):
    return "val=%s" % (self.value)

  def to_json(self):
    return {
      'name':self.name,
      'type': self.t.value,
      'value': self.value
    }

class BlockConfig:

  def __init__(self,inst):
    assert(isinstance(inst,BlockInst))
    self.inst = inst
    self._stmts = {}
    self._modes = None

  @property
  def modes(self):
    return self._modes

  @modes.setter
  def modes(self,ms):
    if len(ms) == 0:
      self._modes = None

    self._modes = []
    for m in ms:
      assert(isinstance(m,blocklib.BlockMode))
      self._modes.append(m)

  def set_config(self,other):
    assert(isinstance(other,BlockConfig))
    assert(other.inst.block == self.inst.block)
    self.modes = other.modes
    self._stmts = {}
    for stmt in other.stmts:
      self.add(stmt)

  def to_json(self):
    return {
      'inst': self.inst.to_json(),
      'modes': list(map(lambda m : m.to_json(),self.modes))  \
      if not self.modes is None else None,
      'stmts': dict(map(lambda el: (el[0],el[1].to_json()), self._stmts.items()))
    }

  @property
  def mode(self):
    assert(self.complete())
    return self.modes[0]

  @property
  def stmts(self):
    for stmt in self._stmts.values():
      yield stmt

  def complete(self):
    return len(self.modes) == 1

  def add(self,stmt):
    assert(not stmt.name in self._stmts)
    self._stmts[stmt.name] = stmt

  def get(self,name):
    if not name in self._stmts:
      raise Exception("unknown identifier <%s> for block config <%s>" % (name,self.inst))
    return self._stmts[name]

  def has(self,name):
    return name in self._stmts

  def __getitem__(self,key):
    assert(key in self._stmts)
    return self._stmts[key]

  @staticmethod
  def make(block,loc):
    cfg = BlockConfig(BlockInst(block.name,loc))
    cfg.modes = block.modes
    for inp in block.inputs:
      cfg.add(PortDataConfig(inp.name))
    for out in block.outputs:
      cfg.add(PortDataConfig(out.name))
    for data in block.data:
      if data.type == blocklib.BlockDataType.CONST:
        cfg.add(ConstDataConfig(data.name,0.0))
      else:
        cfg.add(ExprDataConfig(data.name, \
                               data.args))
    for state in block.state:
      if isinstance(state.impl,blocklib.BCCalibImpl):
        cfg.add(StateConfig(state.name, state.impl.default))
    return cfg

  def __str__(self):
    st = "block %s:\n" % (self.inst)
    indent = "  "
    st += "%s%s\n" % (indent,self.modes)
    for stmt in self.stmts:
      st += "%s%s\n" % (indent,stmt)

    return st


class ADP:

  def __init__(self):
    self.configs = BlockInstanceCollection(self)
    self.tau = 1.0

  def add_instance(self,block,loc):
    assert(isinstance(block,blocklib.Block))
    self.configs.add(BlockConfig.make(block,loc))

  def add_conn(self,srcblk,srcloc,srcport, \
               dstblk,dstloc,dstport):
    raise NotImplementedError
