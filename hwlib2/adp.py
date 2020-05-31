import hwlib2.block as blocklib

class BlockInst:

  def __init__(self,name,loc):
    self.block = name
    self.loc = loc

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

  def get(self,blockname,loc):
    if not blockname in self._collection:
      return None
    if not loc in self._collection[blockname]:
      return None

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


class ConfigStmt:

  def __init__(self,name):
    self.name = name

class ConstDataConfig(ConfigStmt):

  def __init__(self,field,value):
    ConfigStmt.__init__(self,field)
    self.value = value
    self.scf = 1.0

class ExprDataConfig(ConfigStmt):

  def __init__(self,field,args,expr):
    ConfigStmt.__init__(self,field)
    self.args = args
    self.scfs = {}
    self.injs = {}
    self.expr = expr
    for key in args + [field]:
      self.scfs[key] = 1.0
      self.injs[key] = 1.0

class PortDataConfig(ConfigStmt):

  def __init__(self,name):
    ConfigStmt.__init__(self,name)
    self.scf = 1.0

class BlockConfig:

  def __init__(self,inst):
    assert(isinstance(inst,BlockInst))
    self.inst = inst
    self.stmts = {}
    self.modes = []

  @property
  def mode(self):
    assert(self.complete())
    return self.modes[0]

  def complete(self):
    return len(self.modes) == 1

  def add(self,stmt):
    assert(not stmt.name in self.stmts)
    self.stmts[stmt.name] = stmt

  def __getitem__(self,key):
    assert(key in self.stmts)
    return self.stmts[key]

  @staticmethod
  def make(block,loc):
    cfg = BlockConfig(BlockInst(block.name,loc))
    cfg.modes = block.modes
    for inp in block.inputs:
      cfg.add(PortDataConfig(inp.name))
    for out in block.outputs:
      cfg.add(PortDataConfig(out.name))
    for data in block.data:
      if data.type == BlockDataType.CONST:
        cfg.add(ConstDataConfig(data.name))
      else:
        cfg.add(ExprDataConfig(data.name, \
                               data.args))
    return cfg

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
