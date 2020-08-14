import hwlib.block as blocklib
import hwlib.device as devlib
import ops.base_op as baseoplib
from enum import Enum

class BlockInst:

  def __init__(self,name,loc):
    assert(isinstance(name,str))
    assert(isinstance(loc,devlib.Location))
    self.block = name
    self.loc = loc

  @staticmethod
  def from_json(obj):
    loc = devlib.Location.from_json(obj['loc'])
    return BlockInst(obj['block'],loc)

  def to_json(self):
    return {
      'block': self.block,
      'loc': self.loc.to_json()
    }

  def __repr__(self):
    return "%s_%s" % (self.block,"_".join(map(lambda a: str(a), \
                                              self.loc.address)))

  def __eq__(self,other):
    assert(isinstance(other,BlockInst))
    return self.block == other.block and \
      self.loc == other.loc

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

    if (data.inst.loc \
        in self._collection[data.inst.block]):
      raise Exception("location %s of block %s already in use" % (data.inst.loc, \
                                                                  data.inst.block))
    self._collection[data.inst.block][data.inst.loc] = data

  def __getitem__(self,key):
    return self._collection[key]

  def __iter__(self):
    for blk in self._collection:
      for loc in self._collection[blk]:
        yield self._collection[blk][loc]

  def to_json(self):
    return list(map(lambda obj: obj.to_json(),self))



class ConfigStmtType(Enum):
  STATE = "state"
  CONSTANT = "const"
  EXPR = "expr"
  PORT = "port"

class ConfigStmt:

  def __init__(self,type_,name):
    self.name = name
    assert(isinstance(type_,ConfigStmtType))
    self.type = type_

  def pretty_print(self):
    raise NotImplementedError()

  def to_json(self):
    raise NotImplementedError

  @staticmethod
  def from_json(obj):
    typ = ConfigStmtType(obj['type'])
    if typ == ConfigStmtType.CONSTANT:
      return ConstDataConfig.from_json(obj)
    elif typ == ConfigStmtType.PORT:
      return PortConfig.from_json(obj)
    elif typ == ConfigStmtType.STATE:
      return StateConfig.from_json(obj)
    else:
      raise Exception("unhandled from_json: %s" % typ)

  def __repr__(self):
    return "%s %s %s" % (self.name, \
                         self.type.value, \
                         self.pretty_print())

class ConstDataConfig(ConfigStmt):

  def __init__(self,field,value):
    ConfigStmt.__init__(self,ConfigStmtType.CONSTANT,field)
    self.value = value
    self.scf = 1.0

  def pretty_print(self):
    return "val=%f scf=%f" \
      % (self.value,self.scf)

  @staticmethod
  def from_json(obj):
    cfg = ConstDataConfig(obj['name'],obj['value'])
    cfg.scf = obj['scf']
    return cfg

  def to_json(self):
    return {
      'name':self.name,
      'type': self.type.value,
      'scf': self.scf,
      'value': self.value
    }

class ExprDataConfig(ConfigStmt):

  def __init__(self,field,args,expr=None):
    ConfigStmt.__init__(self,ConfigStmtType.EXPR,field)
    self.args = args
    self.scfs = {}
    self.injs = {}
    self.expr = expr
    for key in args + [field]:
      self.scfs[key] = 1.0
      self.injs[key] = 1.0

  @property
  def expr(self):
    return self._expr

  @expr.setter
  def expr(self,e):
    if expr is None:
      self._expr = None

    for v in e.vars():
      if not v in self.args:
        raise Exception("%s is not a valid input. Expected" \
                        % (v,self.args))

    self._expr = expr

  def to_json(self):
    return {
      'name':self.name,
      'expr': self.expr.to_json(),
      'args': self.args.to_json(),
      'scfs': dict(self.scfs),
      'injs': dict(self.injs),
      'args': list(self.args)
    }



class PortConfig(ConfigStmt):

  def __init__(self,name):
    ConfigStmt.__init__(self,ConfigStmtType.PORT,name)
    self._scf = 1.0
    self.source = None

  @property
  def scf(self):
    return self._scf

  @scf.setter
  def scf(self,v):
    assert(v > 0)
    self._scf = v

  def pretty_print(self):
    st = "scf=%f" % (self.scf)
    if not self.source is None:
      st += " src=%s" % self.source
    return st

  def to_json(self):
    return {
      'name':self.name,
      'type': self.type.value,
      'source': self.source.to_json() \
      if not self.source is None else None,
      'scf': self.scf
    }

  @staticmethod
  def from_json(obj):
    cfg = PortConfig(obj['name'])
    cfg.scf = obj['scf']
    if not obj['source'] is None:
      cfg.source = baseoplib.Op.from_json(obj['source'])
    return cfg


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
      'type': self.type.value,
      'value': self.value
    }

  @staticmethod
  def from_json(obj):
    cfg = StateConfig(obj['name'],obj['value'])
    return cfg


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

  @staticmethod
  def from_json(dev,obj):
    inst = BlockInst.from_json(obj['inst'])
    blk = dev.get_block(inst.block)
    cfg = BlockConfig(inst)
    cfg.modes = list(map(lambda m : blk.modes.get(m['values']), \
                         obj['modes']))
    for stmt_obj in obj['stmts'].values():
      st = ConfigStmt.from_json(stmt_obj)
      cfg.add(st)
    return cfg

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

  def stmts_of_type(self,stmt_type):
    for stmt in self.stmts:
      if stmt.type == stmt_type:
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
      cfg.add(PortConfig(inp.name))
    for out in block.outputs:
      cfg.add(PortConfig(out.name))
    for data in block.data:
      if data.type == blocklib.BlockDataType.CONST:
        cfg.add(ConstDataConfig(data.name,0.0))
      else:
        print(data)
        cfg.add(ExprDataConfig(data.name, \
                               data.args, \
                               None))
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

class Connection:

  def __init__(self,src_inst,src_port,dest_inst,dest_port):
    assert(isinstance(src_inst,BlockInst))
    assert(isinstance(src_port,str))
    assert(isinstance(dest_inst,BlockInst))
    assert(isinstance(src_port,str))
    self.source_inst = src_inst
    self.source_port = src_port
    self.dest_inst = dest_inst
    self.dest_port = dest_port

  @staticmethod
  def from_json(obj):
    src_inst = BlockInst.from_json(obj['source_inst'])
    src_port = obj['source_port']
    dest_inst = BlockInst.from_json(obj['dest_inst'])
    dest_port = obj['dest_port']
    return Connection(src_inst, src_port, \
                      dest_inst, dest_port)

  def to_json(self):
    return {
      'source_inst': self.source_inst.to_json(),
      'source_port': self.source_port,
      'dest_inst':self.dest_inst.to_json(),
      'dest_port':self.dest_port

    }

  def __repr__(self):
    return "conn (%s,%s) -> (%s,%s)" % (self.source_inst, \
                                        self.source_port, \
                                        self.dest_inst, \
                                        self.dest_port)

class ADP:

  def __init__(self):
    self.configs = BlockInstanceCollection(self)
    self.conns = []
    self._tau = 1.0

  def copy(self,dev):
    adp = ADP()
    adp.tau = self.tau
    for cfg in self.configs:
      blk = dev.get_block(cfg.inst.block)
      newcfg = adp.add_instance(blk,cfg.inst.loc)
      newcfg.set_config(cfg)

    for conn in self.conns:
      sblk = dev.get_block(conn.source_inst.block)
      dblk = dev.get_block(conn.dest_inst.block)
      adp.add_conn(sblk,
                   conn.source_inst.loc,
                   sblk.outputs[conn.source_port],
                   dblk,
                   conn.dest_inst.loc,
                   dblk.inputs[conn.dest_port])
    return adp

  @property
  def tau(self):
    return self._tau

  @tau.setter
  def tau(self,v):
    assert(v > 0)
    self._tau = v

  def add_source(self,block,loc,port,expr):
    self.configs.get(block.name,loc)[port.name].source = expr

  def add_instance(self,block,loc):
    assert(isinstance(block,blocklib.Block))
    assert(isinstance(loc,devlib.Location))
    cfg = BlockConfig.make(block,loc)
    self.configs.add(cfg)
    return cfg

  def add_conn(self,srcblk,srcloc,srcport, \
               dstblk,dstloc,dstport):
    src_inst = BlockInst(srcblk.name,srcloc)
    if not self.configs.has(src_inst.block,src_inst.loc):
      raise Exception("no configuration for block instance <%s>" % (src_inst))
    dest_inst = BlockInst(dstblk.name,dstloc)
    if not self.configs.has(dest_inst.block,dest_inst.loc):
      raise Exception("no configuration for block instance <%s>" % (dest_inst))
    assert(isinstance(srcport, blocklib.BlockOutput))
    assert(isinstance(dstport, blocklib.BlockInput))
    self.conns.append(
      Connection(
        src_inst,
        srcport.name,
        dest_inst,
        dstport.name
      )
    )

  def port_in_use(self,inst,port):
    for conn in self.conns:
      if conn.source_inst == inst and \
         conn.source_port == port:
        return True
      if conn.dest_inst == inst and \
         conn.dest_port == port:
        return True

    return False

  @staticmethod
  def from_json(board,jsonobj):
    adp = ADP()
    adp.tau = jsonobj['tau']
    for jsonconn in jsonobj['conns']:
      conn = Connection.from_json(jsonconn)
      adp.conns.append(conn)

    for jsonconfig in jsonobj['configs']:
      cfg = BlockConfig.from_json(board,jsonconfig)
      adp.configs.add(cfg)

    return adp

  def to_json(self):
    return {
      'tau':self.tau,
      'conns': list(map(lambda c: c.to_json(), self.conns)),
      'configs': self.configs.to_json()
    }

  def __repr__(self):
    st = []
    def q(stmt):
      st.append(stmt)

    q('tau=%f' % self.tau)
    q('=== connections ===')
    for conn in self.conns:
      q(str(conn))
    q('=== configs ===')
    for config in self.configs:
      q(str(config))

    return "\n".join(st)
