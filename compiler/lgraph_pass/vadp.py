import hwlib.adp as adplib
import hwlib.device as devlib
import ops.op as oplib

class MultiPortVar:
  IDENT = 0
  def __init__(self):
    self.ident = MultiPortVar.IDENT
    MultiPortVar.IDENT += 1


  def copy(self):
    mp = MultiPortVar()
    mp.ident = self.ident
    return mp

  def __repr__(self):
    return "JOIN(%s)" % (self.ident)

'''
class VirtualSourceVar:

  def __init__(self,var):
    self.var = var

  def copy(self):
    return VirtualSourceVar(self.var)

  def __repr__(self):
    return "source-var(%s)" % (self.var)

'''

class LawVar:
  APPLY = "app"

  def __init__(self,law,idx,var=None):
    assert(isinstance(law,str))
    self.law =law
    self.ident = idx
    self.var = var

  def copy(self):
    return LawVar(self.law,self.ident,self.var)


  def make_law_var(self,name):
    return LawVar(self.law,self.ident,name)


  def same_usage(self,other):
    assert(isinstance(other,LawVar))
    return other.ident == self.ident and \
      other.law == self.law

  def __repr__(self):
    if not self.var is None:
      return "%s[%s].%s" % (self.law,self.ident,self.var)
    else:
      return "%s[%s]" % (self.law,self.ident)


class PortVar:

  def __init__(self,block,idx,port=None):
    assert(not isinstance(port,str))
    self.block = block
    self.ident = idx
    self.port = port

  def make_port_var(self,name):
    if isinstance(name,str):
      port = self.block.port(name)
    else:
      port = self.block.port(name.name)

    return PortVar(self.block,self.ident,port)

  def copy(self):
    return PortVar(self.block,self.ident,self.port)

  def __repr__(self):
    if not self.port is None:
      return "%s[%s].%s" % (self.block.name,self.ident,self.port.name)
    else:
      return "%s[%s]" % (self.block.name,self.ident)

class VADPStmt:

  def __init__(self):
    pass

class VADPConn(VADPStmt):

  def __init__(self,src,snk):
    VADPStmt.__init__(self)
    assert(isinstance(src,PortVar)  \
           or isinstance(src,LawVar) or \
           isinstance(src,MultiPortVar))
    assert(isinstance(snk,PortVar)  \
           or isinstance(snk,LawVar) or \
           isinstance(snk,MultiPortVar))
    self.source = src
    self.sink = snk

  def variables(self):
    yield self.source
    yield self.sink


  def copy(self):
    return VADPConn(self.source.copy(),self.sink.copy())

  def __repr__(self):
    return "conn(%s,%s)" % (self.source,self.sink)

class VADPSink(VADPStmt):

  def __init__(self,target,expr):
    VADPStmt.__init__(self)
    assert(isinstance(target,PortVar) or \
           isinstance(target,LawVar) or \
           isinstance(target,MultiPortVar))
    self.dsexpr = expr
    self.target = target

  def variables(self):
    yield self.target


  def copy(self):
    return VADPSink(self.target.copy(),self.dsexpr)

  def __repr__(self):
    return "sink(%s,%s)" % (self.target,self.dsexpr)

class VADPSource(VADPStmt):

  def __init__(self,target,expr):
    VADPStmt.__init__(self)
    if not (isinstance(target,PortVar)) and \
       not (isinstance(target,LawVar)) and \
       not (isinstance(target,MultiPortVar)):
      raise Exception("unexpected target: %s"  \
                      % target.__class__.__name__)
    self.dsexpr = expr
    self.target = target

  def variables(self):
    yield self.target


  def copy(self):
    return VADPSource(self.target.copy(),self.dsexpr)

  def __repr__(self):
    return "source(%s,%s)" % (self.target,self.dsexpr)



class VADPConfig(VADPStmt):

  def __init__(self,target,mode):
    VADPStmt.__init__(self)
    assert(isinstance(target,PortVar) or \
           isinstance(target,LawVar))
    self.target = target
    self.mode = mode
    self.assigns = {}

  def variables(self):
    yield self.target

  def copy(self):
    cfg = VADPConfig(self.target.copy(),self.mode)
    for v,e in self.assigns.items():
      cfg.bind(v,e)
    return cfg

  def same_target(self,other):
    assert(isinstance(other,VADPConfig))
    return self.target == other.target and \
      self.ident == other.ident

  def bind(self,var,value):
    assert(isinstance(var,str))
    assert(not var in self.assigns)
    self.assigns[var] = value

  def __repr__(self):
    return "config(%s,%s)[%s]%s" % (self.target, \
                                    self.target.ident,\
                                    self.mode, \
                                    self.assigns)


def eliminate_joins(stmts):
  target_join = None
  for stmt in stmts:
    for var in stmt.variables():
      if isinstance(var,MultiPortVar):
        target_join = var
        break

  if target_join is None:
    return stmts

  sources = []
  sinks = []
  dsexprs = []
  relevent_stmts = []
  new_vadp = []
  for stmt in stmts:
    if not any(map(lambda v: isinstance(v,MultiPortVar) and \
                   v.ident == target_join.ident, \
                   stmt.variables())):
      new_vadp.append(stmt)
      continue

    relevent_stmts.append(stmt)
    if isinstance(stmt,VADPConn):
      if isinstance(stmt.source,MultiPortVar) and \
         stmt.source.ident == target_join.ident:
        sinks.append(stmt.sink)
      elif isinstance(stmt.sink,MultiPortVar) and \
         stmt.sink.ident == target_join.ident:
        sources.append(stmt.source)
      else:
        raise Exception("impossible. target <%s> must appear" % target_join)

    elif isinstance(stmt,VADPSource):
      assert(isinstance(stmt.target,MultiPortVar) and \
             stmt.target.ident == target_join.ident)
      dsexprs.append(stmt.dsexpr)

    elif isinstance(stmt,VADPSink):
      raise Exception("cannot eliminate joins if vadp is a fragment" % stmt)
    else:
      raise Exception("unsupported statement: %s" % stmt)


  if len(sinks) == 0:
    print("[warn] no sinks.. eliminating join usage")
    return new_vadp


  if len(sinks) != 1:
    for stmt in relevent_stmts:
      print(stmt)
    raise Exception("expected exactly one sink: target=%s sinks=%s" \
                    % (target_join, sinks))

  sink = sinks[0]
  for source in sources:
    new_vadp.append(VADPConn(source,sink))

  for dsexpr in dsexprs:
    new_vadp.append(VADPSource(sink,dsexpr))

  return eliminate_joins(new_vadp)


def is_concrete_vadp(vadp,allow_virtual=False):
  def is_concrete_node(node):
    if isinstance(node,MultiPortVar):
      return allow_virtual
    elif isinstance(node,PortVar):
      return True
    else:
      return False

  for stmt in vadp:
    print(stmt)
    if isinstance(stmt,VADPSource):
      if not is_concrete_node(stmt.target):
        return False
    elif isinstance(stmt,VADPSink):
      if not is_concrete_node(stmt.target):
        return False
    elif isinstance(stmt,VADPConn):
      if not isinstance(stmt.source,PortVar):
        return False
      if not is_concrete_node(stmt.sink):
        return False

    elif isinstance(stmt,VADPConfig):
      if not is_concrete_node(stmt.target):
        return False
      pass
    else:
      raise Exception("unhandled: %s" % stmt)

  return True


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
      if isinstance(stmt.target,PortVar):
        new_stmt.target.ident = get_identifier(stmt.target.block, \
                                               stmt.target.ident)
      yield new_stmt

    elif isinstance(stmt,VADPSink):
      new_stmt = stmt.copy()
      new_stmt.target.ident = get_identifier(stmt.target.block, \
                                           stmt.target.ident)
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
        new_stmt.target.ident = get_identifier(stmt.target.block, \
                                               stmt.target.ident)
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
      block = stmt.target.block
      loc = stmt.target.ident
      adp.add_instance(block,loc)
      cfg = adp.configs.get(block.name,loc)
      cfg.modes = stmt.mode
      for datafield,value in stmt.assigns.items():
        if(isinstance(cfg[datafield], adplib.ExprDataConfig)):
          cfg[datafield].expr = value

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
      block = stmt.target.block
      loc = stmt.target.ident
      port = stmt.target.port
      dsexpr = stmt.dsexpr
      adp.add_source(block,loc,port,dsexpr)


  return adp
