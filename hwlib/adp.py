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

  def copy(self):
    raise NotImplementedError

  def to_json(self):
    raise NotImplementedError

  @staticmethod
  def from_json(obj):
    typ = ConfigStmtType(obj['type'])
    if typ == ConfigStmtType.CONSTANT:
      return ConstDataConfig.from_json(obj)
    elif typ == ConfigStmtType.EXPR:
      return ExprDataConfig.from_json(obj)
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

  def copy(self):
    cfg = ConstDataConfig(self.name,self.value)
    cfg.scf = self.scf
    return cfg

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

  def copy(self):
    cfg = ExprDataConfig(self.name,self.args,expr=self.expr)
    cfg.scfs = dict(self.scfs)
    cfg.injs = dict(self.injs)
    return cfg


  @property
  def expr(self):
    return self._expr

  @expr.setter
  def expr(self,e):
    if e is None:
      self._expr = None
      return

    for v in e.vars():
      if not v in self.args:
        raise Exception("%s is not a valid input. Expected %s" \
                        % (v,self.args))

    self._expr = e

  @staticmethod
  def from_json(obj):
    expr = baseoplib.Op.from_json(obj['expr']) \
           if not obj['expr'] is None \
              else None
    args = obj['args']
    field = obj['name']

    data_op = ExprDataConfig(field=field,expr=expr,args=args)
    for name,scf in obj['scfs'].items():
      assert(name in data_op.scfs)
      data_op.scfs[name] = scf

    for name,inj in obj['injs'].items():
      assert(name in data_op.injs)
      data_op.injs[name] = inj

    return data_op

  def to_json(self):
    return {
      'name':self.name,
      'type': self.type.value,
      'expr': self.expr.to_json(),
      'scfs': dict(self.scfs),
      'injs': dict(self.injs),
      'args': list(self.args)
    }


  def __repr__(self):
    templ = "{name}({args}): {expr}\n"
    st = templ.format(name=self.name, \
                      args=",".join(self.args), \
                      expr=self.expr)

    for field in self.scfs.keys():
      st += "fld %s scf=%f inj=%f\n" \
            % (field,self.scfs[field],self.injs[field])

    return st


class PortConfig(ConfigStmt):

  def __init__(self,name):
    ConfigStmt.__init__(self,ConfigStmtType.PORT,name)
    self._scf = 1.0
    self.source = None

  def copy(self):
    cfg = PortConfig(self.name)
    cfg._scf = self._scf
    cfg.source = self.source
    return cfg


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

  def copy(self):
    return StateConfig(self.name,self.value)

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

  def copy(self):
    cfg = BlockConfig(self.inst)
    cfg.modes = list(self.modes)
    for st in self._stmts.values():
      cfg.add(st.copy())

    return cfg


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
    if not (self.complete()):
      raise Exception("%s incomplete: %s" % (self.inst, \
                                             self.modes))

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
        cfg.add(ExprDataConfig(data.name, \
                               data.inputs, \
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

class ADPConnection:
  WILDCARD = "_"

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
    return ADPConnection(src_inst, src_port, \
                      dest_inst, dest_port)

  @staticmethod
  def test_str(st,test_st):
    assert(isinstance(st,str))
    return test_st == ADPConnection.WILDCARD or \
      st == test_st

  @staticmethod
  def is_wildcard(st):
    return st == ADPConnection.WILDCARD

  def test_addr(loc,addr):
    assert(len(loc) == len(addr))
    for a1,a2 in zip(loc,addr):
      if a2 != ADPConnection.WILDCARD and \
         a1 != a2:
        return False
    return True


  def dest_match(self,block_name,loc,port):
    assert(isinstance(block_name,str))
    block_match = ADPConnection.test_str(self.dest_inst.block,block_name)
    port_match = ADPConnection.test_str(self.dest_port,port)
    loc_match = ADPConnection.test_addr(self.dest_inst.loc,loc)
    return block_match and port_match and loc_match

  def source_match(self,block_name,loc,port):
    assert(isinstance(block_name,str))
    block_match = ADPConnection.test_str(self.source_inst.block,block_name)
    port_match = ADPConnection.test_str(self.source_port,port)
    loc_match = ADPConnection.test_addr(self.source_inst.loc,loc)
    return block_match and port_match and loc_match

  def same_source(self,other):
    assert(isinstance(other,ADPConnection))
    return self.source_inst == other.source_inst and \
      self.source_port == other.source_port


  def same_dest(self,other):
    assert(isinstance(other,ADPConnection))
    return self.dest_inst == other.dest_inst and \
      self.dest_port == other.dest_port

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

class ADPMetadata:
  class Keys(Enum):
    LGRAPH_ID = "lgraph_id"
    LSCALE_ID = "lscale_id"
    LSCALE_SCALE_METHOD = "lscale_method"
    LSCALE_OBJECTIVE = "lscale_objective"
    RUNTIME_CALIB_OBJ = "runt_calib_obj"
    RUNTIME_PHYS_DB = "runt_phys_db"
    LSCALE_AQM = "aqm"
    LSCALE_DQM = "dqm"
    DSNAME = "dsname"
    FEATURE_SUBSET = "subset"

  def __init__(self):
    self._meta = {}

  def set(self,key,val):
    assert(isinstance(key,ADPMetadata.Keys))
    self._meta[key] = val

  def copy(self):
    meta = ADPMetadata()
    for k,v in self._meta.items():
      meta.set(k,v)
    return meta

  @staticmethod
  def from_json(obj):
    meta  = ADPMetadata()
    for k,v in obj['meta'].items():
      mkey = ADPMetadata.Keys(k)
      meta.set(mkey,v)
    return meta

  def to_json(self):
    return {
      'meta':dict(map(lambda tup: (tup[0].value,tup[1]), \
                      self._meta.items()))
    }

  def has(self,key):
    return key in self._meta

  def get(self,key):
    return self[key]

  def __getitem__(self,k):
    if not k in self._meta:
      raise Exception("key <%s> not in metadata (%s)" \
                      % (k,self._meta.keys()))
    return self._meta[k]

  def __repr__(self):
    st = ""
    for k,v in self._meta.items():
      st += "%s=%s\n" % (k.value,v)
    return st

class ADP:

  def __init__(self):
    self.configs = BlockInstanceCollection(self)
    self.conns = []
    self.metadata = ADPMetadata()
    self._tau = 1.0

  def copy(self,dev):
    adp = ADP()
    adp.tau = self.tau
    adp.metadata = self.metadata.copy()
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


  def outgoing_conns(self,block_name,loc,port):
    for conn in self.conns:
      if conn.source_match(block_name,loc,port):
        yield conn


  def incoming_conns(self,block_name,loc,port):
    for conn in self.conns:
      if conn.dest_match(block_name,loc,port):
        yield conn


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
    if not isinstance(loc,devlib.Location):
      raise Exception("not a location: <%s>" % str(loc))

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
      ADPConnection(
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

  def observable_ports(self,board):
    variables = {}
    for cfg in self.configs:
        blk = board.get_block(cfg.inst.block)
        for out in blk.outputs:
            for pininfo in board.get_external_pins(blk, \
                                                   cfg.inst.loc, \
                                                   out.name):
                port_cfg = cfg[out.name]
                varname = port_cfg.source.name
                scf = port_cfg.scf
                if not varname in variables:
                    variables[varname] = {'chans':{}, \
                                          'scf':port_cfg.scf}

                variables[varname]['chans'][pininfo.channel] = pininfo

    for var,data in variables.items():
      yield var,data['scf'],data['chans']

  @staticmethod
  def from_json(board,jsonobj):
    adp = ADP()
    adp.tau = jsonobj['tau']
    adp.metadata = ADPMetadata.from_json(jsonobj['metadata'])

    for jsonconn in jsonobj['conns']:
      conn = ADPConnection.from_json(jsonconn)
      adp.conns.append(conn)

    for jsonconfig in jsonobj['configs']:
      cfg = BlockConfig.from_json(board,jsonconfig)
      adp.configs.add(cfg)

    return adp

  def to_json(self):
    return {
      'tau':self.tau,
      'metadata':self.metadata.to_json(),
      'conns': list(map(lambda c: c.to_json(), self.conns)),
      'configs': self.configs.to_json()
    }

  def __repr__(self):
    st = []
    def q(stmt):
      st.append(stmt)

    q('tau=%f' % self.tau)
    q('=== metadata ===')
    for key,value in self.metadata:
      q("field %s = %s" % (key.value,value))

    q('=== connections ===')
    for conn in self.conns:
      q(str(conn))
    q('=== configs ===')
    for config in self.configs:
      q(str(config))

    return "\n".join(st)
