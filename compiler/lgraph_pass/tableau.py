import hwlib.block as blocklib
import compiler.lgraph_pass.unify as unifylib
from compiler.lgraph_pass.tableau_data import *
import ops.base_op as oplib
import numpy as np

def make_initial_tableau(blocks,laws,variable,expr):
  tab = Tableau()
  tab.add_goal(Goal(DSVar(variable),blocklib.BlockSignalType.ANALOG,expr))
  for block in blocks:
    for output in block.outputs:
      for expr,modes in output.relation.get_by_property():
        for mode in modes:
          rel = PortRelation(block,0,mode,output,expr)
          tab.add_relation(rel)

  for law_data in laws:
    law = PhysicsLawRelation(law_data['name'],0, \
                             law_data['type'], \
                             law_data['expr'], \
                             law_data['apply'], \
                             law_data['simplify'])
    for var,typ in law_data['vars'].items():
      law.decl_var(var,typ)

    tab.add_relation(law)

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

def derive_tableau_from_phys_rel(tableau,goal,rel,unif):
  new_tableau = tableau.copy()
  new_tableau.remove_goal(goal)


  app_var = LawVar(rel.law,rel.ident,LawVar.APPLY)
  for stmt in rel.apply(goal):
    new_tableau.add_stmt(stmt)

  for law_var,e in unif.assignments:
    new_tableau.add_goal(Goal(LawVar(rel.law, \
                                     rel.ident, \
                                     law_var), \
                              rel.get_type(law_var.name),e))

  for curr_rel in new_tableau.relations:
      if isinstance(curr_rel,PhysicsLawRelation) and \
          curr_rel.same_usage(rel):
        curr_rel.ident += 1


  return new_tableau

def derive_tableaus(tableau,goal):
  for rel in tableau.relations:
    if rel.typecheck(goal):
      print(rel)
      print(goal)
      print("====")
      if isinstance(rel,PortRelation):
        for unif in unifylib.unify(rel.expr,goal.expr,rel.cstrs):
          new_tableau = derive_tableau_from_port_rel(tableau,goal,rel,unif)
          yield new_tableau

      elif isinstance(rel,PhysicsLawRelation):
        cstrs = dict(map(lambda v: (v,unifylib.UnifyConstraint.NONE), \
                         rel.variables))
        for unif in unifylib.unify(rel.expr,goal.expr,cstrs):
          new_tableau = derive_tableau_from_phys_rel(tableau,goal,rel,unif)
          yield new_tableau

      else:
        raise Exception("unknown relation")

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
