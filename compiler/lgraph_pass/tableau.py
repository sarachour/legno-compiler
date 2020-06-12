import hwlib.block as blocklib
import compiler.lgraph_pass.unify as unifylib
import ops.base_op as oplib
import numpy as np

class TableauVar:

  def __init__(self):
    pass

class DSVar(TableauVar):
  def __init__(self,var):
    self.var = var

  def __repr__(self):
    return self.var

class LawVar(TableauVar):
  def __init__(self,law,idx,var):
    self.law =law
    self.ident = idx
    self.variable =var

  def __repr__(self):
    return "%s[%s].%s" % (self.law,self.ident,self.variable)


class PortVar(TableauVar):
  def __init__(self,block,idx,port):
    self.block = block
    self.ident = idx
    self.port = port

  def __repr__(self):
    return "%s[%s].%s" % (self.block.name,self.ident,self.port.name)

class Goal:

  def __init__(self,var,typ,expr):
    assert(isinstance(var,TableauVar))
    self.variable = var
    self.type = typ
    self.expr = expr

  def complexity(self):
    return self.expr.nodes()

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

  def copy(self):
    rel = PortRelation(self.block,self.ident,self.modes, \
                       self.port,self.expr)
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
    assert(isinstance(src,PortVar) or isinstance(src,LawVar))
    assert(isinstance(snk,PortVar) or isinstance(snk,LawVar))
    self.source = src
    self.sink = snk

  def __repr__(self):
    return "conn(%s,%s)" % (self.source,self.sink)

class VADPSource(VADPStmt):

  def __init__(self,port,expr):
    VADPStmt.__init__(self)
    assert(isinstance(port,PortVar))
    self.dsexpr = expr
    self.port = port

  def __repr__(self):
    return "source(%s,%s)" % (self.port,self.dsexpr)

class VADPSink(VADPStmt):

  def __init__(self,port,name):
    VADPStmt.__init__(self)
    assert(isinstance(port,PortVar))
    assert(isinstance(name,str))
    self.dsvar = name
    self.port = port

  def __repr__(self):
    return "sink(%s,%s)" % (self.port,self.dsvar)



class VADPConfig(VADPStmt):

  def __init__(self,block,ident,mode):
    VADPStmt.__init__(self)
    self.block = block
    self.ident = ident
    self.mode = mode
    self.assigns = {}

  def bind(self,var,value):
    assert(isinstance(var,str))
    assert(not var in self.assigns)
    self.assigns[var] = value

  def __repr__(self):
    return "config(%s,%d)[%s]%s" % (self.block.name, \
                                    self.ident,\
                                    self.mode, \
                                    self.assigns)

class LawRelation:

  def __init__(self,law,idx,typ,expr):
    self.law = law
    self.ident = idx
    self.variables = expr.vars()
    self.expr = expr
    self.type = typ
    self.var_types = dict(map(lambda v: (v,None), self.variables))

class Tableau:

  def __init__(self):
    self.goals = []
    self.relations = []
    self.vadp = []

  def complexity(self):
    return max(map(lambda g: g.complexity(), self.goals))

  def add_stmt(self,vadp_st):
    assert(isinstance(vadp_st,VADPStmt))
    self.vadp.append(vadp_st)
  def copy(self):
    tab = Tableau()
    tab.goals = list(self.goals)
    tab.relations = list(map(lambda rel: rel.copy(), self.relations))
    tab.vadp = list(self.vadp)
    return tab

  def success(self):
    return len(self.goals) == 0

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
           isinstance(rel,LawRelation))
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

    return st


def make_initial_tableau(blocks,laws,variable,expr):
  tab = Tableau()
  tab.add_goal(Goal(DSVar(variable),blocklib.BlockSignalType.ANALOG,expr))
  print(tab)
  input()
  for block in blocks:
    for output in block.outputs:
      for expr,modes in output.relation.get_by_property():
        for mode in modes:
          rel = PortRelation(block,0,mode,output,expr)
          tab.add_relation(rel)

  return tab

def derive_tableau_from_port_rel(tableau,goal,rel,unif):
  new_tableau = tableau.copy()
  new_tableau.remove_goal(goal)

  out_port = PortVar(rel.block,rel.ident,rel.port)
  if isinstance(goal.variable,DSVar):
    new_tableau.add_stmt(VADPSink(out_port,goal.variable.var))
  elif isinstance(goal.variable,PortVar):
    in_port = PortVar(goal.variable.block, \
                          goal.variable.ident, \
                          goal.variable.port)
    new_tableau.add_stmt(VADPConn(out_port,in_port))
  else:
    print("TODO: vadp should find/replace laws.")

  vadp_cfg = VADPConfig(rel.block,rel.ident,rel.modes)
  # translate assignments to goals
  for vop,e in unif.assignments:
    v = vop.name
    # binding input port assignment
    if rel.block.inputs.has(v):
      if e.op == oplib.OpType.VAR:
        new_tableau.add_stmt(VADPSource(PortVar(rel.block, \
                                                rel.ident, \
                                                rel.port), e))
      else:
        sig_type = rel.block.inputs[v].type
        new_tableau.add_goal(Goal(PortVar(rel.block, \
                                          rel.ident, \
                                          rel.block.inputs[v]), \
                                  sig_type,e))
    elif rel.block.data.has(v):
      vadp_cfg.bind(v,e)
    else:
      raise Exception("dne")

  new_tableau.add_stmt(vadp_cfg)

  for curr_rel in new_tableau.relations:
      if isinstance(curr_rel,PortRelation) and \
          curr_rel.same_block(rel):
        curr_rel.ident += 1

  return new_tableau

def derive_tableaus(tableau,goal):
  for rel in tableau.relations:
    if rel.typecheck(goal):
      print(rel)
      print(goal)
      print("====")
      for unif in unifylib.unify(rel.expr,goal.expr,rel.cstrs):
        new_tableau = derive_tableau_from_port_rel(tableau,goal,rel,unif)
        yield new_tableau

def get_valid_tableaus(frontier,depth):
  for tab,idx in frontier:
    assert(not tab.success())
    if idx < depth:
      yield tab,idx

def select_tableau(frontier):
  penalty = list(map(lambda tab: tab[0].complexity(), frontier))
  idx = np.argmin(penalty)
  tableau,tableau_depth = frontier[idx]
  other_tableaus = list(map(lambda i: frontier[i], \
                            filter(lambda i: i != idx, \
                                   range(0,len(frontier)))))
  return tableau,tableau_depth,other_tableaus

def search(blocks,laws,variable,expr,depth=5):
  tableau = make_initial_tableau(blocks,laws, \
                                 variable,expr)

  frontier = [(tableau,0)]

  next_frontier = []
  valid_tableaus = list(get_valid_tableaus(frontier,depth))
  while len(valid_tableaus) > 0:
    tableau,tab_depth,other_tableaus = select_tableau(valid_tableaus)
    next_frontier = other_tableaus

    goal = tableau.goals[0]
    for new_tableau in derive_tableaus(tableau,goal):
      if new_tableau.success():
        print(new_tableau.vadp)
        input("found solution")
        yield new_tableau.vadp
      else:
        next_frontier.append((new_tableau,tab_depth + 1))

    valid_tableaus = list(get_valid_tableaus(next_frontier,depth))


  raise NotImplementedError
