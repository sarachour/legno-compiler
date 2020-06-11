import hwlib.block as blocklib
import compiler.lgraph_pass.unify as unifylib

class Goal:

  def __init__(self,var,typ,expr):
    self.variable = var
    self.type = typ
    self.expr = expr

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

  def typecheck(self,goal):
    if goal.type is None:
      return True
    output_type = self.port.type
    return goal.type == output_type

  def __repr__(self):
    output_type = self.port.type
    return "rel %s(%d,%s) : %s = %s" % (self.block.name,self.ident, \
                                        self.port.name, \
                                        self.port.type,self.expr)


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

  def success(self):
    return len(self.goals) == 0

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

def make_initial_tableau(blocks,laws,variable,expr):
  tab = Tableau()
  tab.add_goal(Goal(variable,None,expr))

  for block in blocks:
    print(block.name)
    for output in block.outputs:
      for expr,modes in output.relation.get_by_property():
        for mode in modes:
          rel = PortRelation(block,0,mode,output,expr)
          tab.add_relation(rel)
          print(rel)

  return tab

def search(blocks,laws,variable,expr,depth=10):
  tableau = make_initial_tableau(blocks,laws, \
                                 variable,expr)

  frontier = [tableau]

  next_frontier = []
  for tableau in frontier:
    if tableau.success():
      yield tableau._vadp

    goal = tableau.goals[0]
    for rel in tableau.relations:
      if rel.typecheck(goal):
        print("%s UNIFY %s" % (goal,rel))
        for result in unifylib.unify(rel.expr,goal.expr,rel.cstrs):
          print(result)
