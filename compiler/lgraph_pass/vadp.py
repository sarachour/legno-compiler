import hwlib.adp as adplib
import hwlib.device as devlib

class VirtualSourceVar:

  def __init__(self,var):
    self.var = var

  def copy(self):
    return VirtualSourceVar(self.var)

  def __repr__(self):
    return "source-var(%s)" % (self.var)

class LawVar:
  APPLY = "app"

  def __init__(self,law,idx,var):
    self.law =law
    self.ident = idx
    self.var = var

  def same_usage(self,other):
    assert(isinstance(other,LawVar))
    return other.ident == self.ident and \
      other.law == self.law

  def __repr__(self):
    return "%s[%s].%s" % (self.law,self.ident,self.var)



class PortVar:

  def __init__(self,block,idx,port):
    assert(not isinstance(port,str))
    self.block = block
    self.ident = idx
    self.port = port

  def copy(self):
    return PortVar(self.block,self.ident,self.port)

  def __repr__(self):
    return "%s[%s].%s" % (self.block.name,self.ident,self.port.name)

class VADPStmt:

  def __init__(self):
    pass

class VADPConn(VADPStmt):

  def __init__(self,src,snk):
    VADPStmt.__init__(self)
    assert(isinstance(src,PortVar)  \
           or isinstance(src,LawVar))
    assert(isinstance(snk,PortVar)  \
           or isinstance(snk,LawVar) or \
           isinstance(snk,VirtualSourceVar))
    self.source = src
    self.sink = snk

  def copy(self):
    return VADPConn(self.source.copy(),self.sink.copy())

  def __repr__(self):
    return "conn(%s,%s)" % (self.source,self.sink)

class VADPSink(VADPStmt):

  def __init__(self,port,expr):
    VADPStmt.__init__(self)
    assert(isinstance(port,PortVar) or \
           isinstance(port,LawVar))
    self.dsexpr = expr
    self.port = port

  def copy(self):
    return VADPSink(self.port.copy(),self.dsexpr)

  def __repr__(self):
    return "sink(%s,%s)" % (self.port,self.dsexpr)

class VADPSource(VADPStmt):

  def __init__(self,port,expr):
    VADPStmt.__init__(self)
    if not (isinstance(port,PortVar)) and \
       not (isinstance(port,LawVar)) and \
       not (isinstance(port,VirtualSourceVar)):
      raise Exception("unexpected port: %s"  \
                      % port.__class__.__name__)
    self.dsexpr = expr
    self.port = port

  def copy(self):
    return VADPSource(self.port.copy(),self.dsexpr)

  def __repr__(self):
    return "source(%s,%s)" % (self.port,self.dsexpr)



class VADPConfig(VADPStmt):

  def __init__(self,block,ident,mode):
    VADPStmt.__init__(self)
    self.block = block
    self.ident = ident
    self.mode = mode
    self.assigns = {}

  def copy(self):
    cfg = VADPConfig(self.block,self.ident,self.mode)
    for v,e in self.assigns.items():
      cfg.bind(v,e)
    return cfg

  def same_block(self,other):
    assert(isinstance(other,VADPConfig))
    return self.block == other.block and \
      self.ident == other.ident

  def bind(self,var,value):
    assert(isinstance(var,str))
    assert(not var in self.assigns)
    self.assigns[var] = value

  def __repr__(self):
    return "config(%s,%s)[%s]%s" % (self.block.name, \
                                    self.ident,\
                                    self.mode, \
                                    self.assigns)

def is_concrete_vadp(vadp,allow_virtual=False):
  def is_concrete_node(node):
    if isinstance(node,VirtualSourceVar):
      return allow_virtual
    elif isinstance(node,PortVar):
      return True
    else:
      return False

  for stmt in vadp:
    if isinstance(stmt,VADPSource):
      if not is_concrete_node(stmt.port):
        return False
    elif isinstance(stmt,VADPSink):
      if not isinstance(stmt.port,PortVar):
        return False
    elif isinstance(stmt,VADPConn):
      if not isinstance(stmt.source,PortVar):
        return False
      if not is_concrete_node(stmt.sink):
        return False

    elif isinstance(stmt,VADPConfig):
      pass
    else:
      raise Exception("unhandled: %s" % stmt)

  return True

def get_virtual_variable_sources(vadp,virtvar):
  assert(isinstance(virtvar,VirtualSourceVar))

  sources = []
  for stmt in vadp:
    if isinstance(stmt, VADPConn) and \
      isinstance(stmt.sink,VirtualSourceVar) and \
      stmt.sink.var == virtvar.var:
      sources.append(stmt.source)

  return sources


def remap_vadp_identifiers(insts,fragment):
  mappings = {}
  def get_identifier(block,inst):
    if not (block.name,inst) in mappings:
      if not block.name in insts:
        insts[block.name] = 0

      mappings[(block.name,inst)] = insts[block.name]
      insts[block.name] += 1

    return mappings[(block.name,inst)]

  for stmt in fragment:
    if isinstance(stmt,VADPSource) or \
       isinstance(stmt,VADPSink):
      new_stmt = stmt.copy()
      if isinstance(stmt.port,PortVar):
        new_stmt.port.ident = get_identifier(stmt.port.block, \
                                             stmt.port.ident)
      yield new_stmt

    elif isinstance(stmt,VADPSink):
      new_stmt = stmt.copy()
      new_stmt.port.ident = get_identifier(stmt.port.block, \
                                           stmt.port.ident)
      yield new_stmt

    elif isinstance(stmt,VADPConn):
        new_stmt = stmt.copy()
        new_stmt.source.ident = get_identifier(stmt.source.block, \
                                               stmt.source.ident)
        if isinstance(stmt.sink,PortVar):
          new_stmt.sink.ident = get_identifier(stmt.sink.block, \
                                               stmt.sink.ident)
        yield new_stmt

    elif isinstance(stmt,VADPConfig):
        new_stmt = stmt.copy()
        new_stmt.ident = get_identifier(stmt.block, \
                                   stmt.ident)
        yield new_stmt

    else:
        raise Exception("not handled: %s" % stmt)


def remap_vadps(vadps,insts={}):
  stmts = []
  for frag_index,vadp_prog in enumerate(vadps):
    for stmt in remap_vadp_identifiers(insts,vadp_prog):
      stmts.append(stmt)

  return stmts

def to_adp(vadps):
  adp = adplib.ADP()
  for stmt in vadps:
    if isinstance(stmt,VADPConfig):
      block = stmt.block
      loc = stmt.ident
      adp.add_instance(block,loc)
      cfg = adp.configs.get(block.name,loc)
      cfg.modes = stmt.mode
      for datafield,value in stmt.assigns.items():
        if(isinstance(cfg[datafield], adplib.ExprDataConfig)):
          raise NotImplementedError
        elif(isinstance(cfg[datafield], adplib.ConstDataConfig)):
          cfg[datafield].value = value.compute()
        else:
          raise Exception("cannot set field <%s>" % datafield)

    elif isinstance(stmt,VADPConn):
      sb = stmt.source.block
      sl = stmt.source.ident
      sp = stmt.source.port
      db = stmt.sink.block
      dl = stmt.sink.ident
      dp = stmt.sink.port
      adp.add_conn(sb,sl,sp,db,dl,dp)

  for stmt in vadps:
    if isinstance(stmt,VADPSource):
      block = stmt.port.block
      loc = stmt.port.ident
      port = stmt.port.port
      dsexpr = stmt.dsexpr
      adp.add_source(block,loc,port,dsexpr)


  return adp
