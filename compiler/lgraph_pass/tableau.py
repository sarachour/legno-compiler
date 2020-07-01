import hwlib.block as blocklib
import compiler.lgraph_pass.unify as unifylib
import ops.base_op as oplib

class TableauVar:

  def __init__(self):
    pass

class DSVar(TableauVar):
  def __init__(self,var):
    self.var = var

  def __repr__(self):
    return self.var

class LawVar(TableauVar):
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


class VirtualSourceVar(TableauVar):

  def __init__(self,var):
    self.var = var

  def copy(self):
    return VirtualSourceVar(self.var)

  def __repr__(self):
    return "source-var(%s)" % (self.var)


class PortVar(TableauVar):

  def __init__(self,block,idx,port):
    assert(not isinstance(port,str))
    self.block = block
    self.ident = idx
    self.port = port

  def copy(self):
    return PortVar(self.block,self.ident,self.port)

  def __repr__(self):
    return "%s[%s].%s" % (self.block.name,self.ident,self.port.name)

class Goal:

  def __init__(self,var,typ,expr):
    assert(isinstance(var,TableauVar))
    self.variable = var
    self.type = typ
    self.expr = expr

  def equals(self,g2):
    return str(self) == str(g2)

  def __repr__(self):
    return "goal %s : %s = %s" % (self.variable,self.type,self.expr)

class PortRelation:

  def __init__(self,block,idx,modes,port,expr):
    self.block = block
    self.ident = idx
    self.modes = modes
    self.port = port
    self.expr = expr
    self.cstrs = dict(map(lambda v: (v,unifylib.UnifyConstraint.NONE), \
                          self.expr.vars()))
    for var in self.cstrs.keys():
      if self.block.data.has(var) and \
         self.block.data[var].type == blocklib.BlockDataType.CONST:
        self.cstrs[var] = unifylib.UnifyConstraint.CONSTANT

      elif self.block.data.has(var) and \
         self.block.data[var].type == blocklib.BlockDataType.EXPR:
        self.cstrs[var] = unifylib.UnifyConstraint.FUNCTION

  def equals(self,g2):
    return str(self) == str(g2)

  def copy(self):
    rel = PortRelation(self.block, \
                       self.ident, \
                       self.modes, \
                       self.port, \
                       self.expr)
    rel.cstrs = dict(self.cstrs)
    return rel

  def same_block(self,rel):
    if not isinstance(rel,PortRelation):
      return False

    return self.block.name == rel.block.name and \
      self.ident == rel.ident

  def typecheck(self,goal):
    assert(isinstance(goal,Goal))
    if goal.type is None:
      return True
    output_type = self.port.type
    return goal.type == output_type

  def __repr__(self):
    output_type = self.port.type
    return "rel %s(%d,%s) : %s = %s" % (self.block.name,self.ident, \
                                        self.port.name, \
                                        self.port.type,self.expr)

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
    assert(isinstance(port,PortVar))
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
    return "config(%s,%d)[%s]%s" % (self.block.name, \
                                    self.ident,\
                                    self.mode, \
                                    self.assigns)

class PhysicsLawRelation:

  def __init__(self,law,idx,typ,expr,apply,simplify,cstr_fn):
    self.law = law
    self.ident = idx
    self.variables = expr.vars()
    self.expr = expr
    self.type = typ
    self._apply_fn = apply
    self._simplify_fn = simplify
    self._cstr_fn = cstr_fn
    self.var_types = dict(map(lambda v: (v,None), self.variables))

  def equals(self,g2):
    return str(self) == str(g2)

  def same_usage(self,other):
    assert(isinstance(other,PhysicsLawRelation))
    return self.law == other.law and \
      self.ident == other.ident


  def constraints(self,variables):
    return self._cstr_fn(variables)

  def simplify(self,vadp):
    simplified = True
    while simplified:
      simplified,vadp = self._simplify_fn(vadp,self)

    return vadp


  def apply(self,goal):
    for stmt in self._apply_fn(goal,self):
      yield stmt

  def copy(self):
    rel = PhysicsLawRelation(self.law, \
                             self.ident, \
                             self.type, \
                             self.expr, \
                             self._apply_fn, \
                             self._simplify_fn, \
                             self._cstr_fn)
    for v,t in self.var_types.items():
      rel.decl_var(v,t)

    return rel

  def get_type(self,var):
    assert(isinstance(var,str))
    assert(var in self.variables)
    return self.var_types[var]

  def typecheck(self,goal):
    assert(isinstance(goal,Goal))
    if goal.type is None:
      return True
    return goal.type == self.type

  def decl_var(self,var_name,typ):
    assert(var_name in self.variables)
    if not self.var_types[var_name] is None:
      assert(self.var_types[var_name] == typ)
    self.var_types[var_name] = typ

  def __repr__(self):
    return "%s(%d):%s = %s" % (self.law,self.ident,self.type,self.expr)

class Tableau:

  def __init__(self):
    self.goals = []
    self.relations = []
    self.vadp = []

  def add_stmt(self,vadp_st):
    assert(isinstance(vadp_st,VADPStmt))
    self.vadp.append(vadp_st)

  def copy(self):
    tab = Tableau()
    tab.goals = list(self.goals)
    tab.relations = list(map(lambda rel: rel.copy(), \
                             self.relations))
    tab.vadp = list(self.vadp)
    return tab

  def success(self):
    return len(self.goals) == 0

  def remove_relation(self,relation):
    assert(isinstance(relation,PortRelation) or \
           isinstance(relation,LawRelation))
    g = list(filter(lambda g: not relation.equals(g), \
                    self.relations))
    assert(len(g) >= len(self.relations)-1)
    self.relations = g


  def remove_goal(self,goal):
    assert(isinstance(goal,Goal))
    g = list(filter(lambda g: not goal.equals(g), \
                    self.goals))
    assert(len(g) >= len(self.goals)-1)
    self.goals = g


  def add_goal(self,goal):
    assert(isinstance(goal,Goal))
    self.goals.append(goal)

  def add_relation(self,rel):
    assert(isinstance(rel,PortRelation) or \
           isinstance(rel,PhysicsLawRelation))
    self.relations.append(rel)

  def typecheck(self,goal):
    if goal.typ is None:
      return True
    return goal.type == self.type

  def __repr__(self):
    st = "<<< GOALS >>>\n"
    for goal in self.goals:
      st += "%s\n" % goal

    st += "<<< RELATIONS >>>\n"
    for rel in self.relations:
      st += "%s\n" % rel

    st += "<<< VADP >>>\n"
    for stmt in self.vadp:
      st += "%s\n" % stmt


    return st


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
      if isinstance(stmt,PortVar):
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
  for vadp_prog in vadps:
    for stmt in remap_vadp_identifiers(insts,vadp_prog):
      stmts.append(stmt)

  return stmts


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
