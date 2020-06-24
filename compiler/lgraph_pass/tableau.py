import hwlib.block as blocklib
import compiler.lgraph_pass.unify as unifylib
from compiler.lgraph_pass.tableau_data import *
import ops.base_op as oplib
import ops.generic_op as genoplib
import numpy as np

def make_initial_tableau(blocks,laws,variable,expr):
  tab = Tableau()
  tab.add_goal(Goal(DSVar(variable),blocklib.BlockSignalType.ANALOG,expr))
  for block in blocks:
    for output in block.outputs:
      for expr,modes in output.relation.get_by_property():
        rel = PortRelation(block,0,modes,output,expr)
        tab.add_relation(rel)

  for law_data in laws:
    law = PhysicsLawRelation(law_data['name'],0, \
                             law_data['type'], \
                             law_data['expr'], \
                             law_data['apply'], \
                             law_data['simplify'], \
                             law_data['cstrs'])
    for var,typ in law_data['vars'].items():
      law.decl_var(var,typ)

    tab.add_relation(law)

  return tab

def apply_vadp_config_to_relation(block,vadp_cfg,unif,curr_rel):
  valid_modes = list(set(vadp_cfg.mode) \
                     .intersection(set(curr_rel.modes)))
  if len(valid_modes) == 0:
    return False

  curr_rel.modes = valid_modes
  assigns = {}
  variables = []
  for v,e in unif.assignments:
    assigns[v.name] = e
    variables += e.vars()
  for v,e in vadp_cfg.assigns.items():
    assigns[v] = e
    variables += e.vars()

  curr_rel.expr = curr_rel.expr.substitute(assigns)
  for v in variables:
    curr_rel.cstrs[v] = unifylib.UnifyConstraint.SAMEVAR

  return True

def derive_tableau_from_port_rel(tableau,goal,rel,unif):
  new_tableau = tableau.copy()
  new_tableau.remove_goal(goal)

  out_port = PortVar(rel.block,rel.ident,rel.port)
  if isinstance(goal.variable,DSVar):
    assert(rel.block.outputs.has(rel.port.name))
    new_tableau.add_stmt(VADPSource(out_port, \
                                    genoplib.Var(goal.variable.var)))
  elif isinstance(goal.variable,PortVar):
    in_port = PortVar(goal.variable.block, \
                          goal.variable.ident, \
                          goal.variable.port)
    new_tableau.add_stmt(VADPConn(out_port,in_port))
  elif isinstance(goal.variable,LawVar):
    in_port = LawVar(goal.variable.law, \
                     goal.variable.ident, \
                     goal.variable.var)
    new_tableau.add_stmt(VADPConn(out_port,in_port))

  else:
    raise Exception("TODO: vadp should find/replace laws.")

  vadp_cfg = VADPConfig(rel.block,rel.ident,rel.modes)
  for stmt in tableau.vadp:
    if isinstance(stmt,VADPConfig) and \
       stmt.same_block(vadp_cfg):
      stmt.merge(vadp_cfg)
      vadp_cfg = stmt

  # translate assignments to goals
  for vop,e in unif.assignments:
    v = vop.name
    # binding input port assignment
    if rel.block.inputs.has(v):
      sig_type = rel.block.inputs[v].type
      new_tableau.add_goal(Goal(PortVar(rel.block, \
                                        rel.ident, \
                                        rel.block.inputs[v]), \
                                sig_type,e))
    elif rel.block.data.has(v):
      vadp_cfg.bind(v,e)
    elif rel.cstrs[v] == unifylib.UnifyConstraint.SAMEVAR:
      pass
    else:
      print(rel)
      print(rel.cstrs)
      print(rel.modes)
      raise Exception("unknown: %s=%s" % (v,e))

  new_tableau.add_stmt(vadp_cfg)

  for curr_rel in new_tableau.relations:
    if isinstance(curr_rel,PortRelation) and \
       curr_rel.same_block(rel):
      # create new block
      exists = any(filter(lambda r:
                          isinstance(r,PortRelation) and \
                          r.ident == curr_rel.ident + 1 and \
                          r.block.name == curr_rel.block.name and \
                          r.port.name == curr_rel.port.name,
                          new_tableau.relations))

      if not exists:
        new_rel = curr_rel.copy()
        new_rel.ident += 1
        new_tableau.add_relation(new_rel)

      if curr_rel.equals(rel):
        new_tableau.remove_relation(rel)

      elif not apply_vadp_config_to_relation(curr_rel.block, \
                                             vadp_cfg, \
                                             unif, \
                                             curr_rel):
        new_tableau.remove_relation(curr_rel)


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
      if isinstance(rel,PortRelation):
        if rel.same_block(goal.variable):
          continue

        for unif in unifylib.unify(rel.expr,goal.expr,rel.cstrs):
          new_tableau = derive_tableau_from_port_rel(tableau,goal,rel,unif)
          yield new_tableau

      elif isinstance(rel,PhysicsLawRelation):
        cstrs = rel.constraints(rel.variables)
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

def tableau_complexity(tableau):
  cost = 0.0
  for goal in tableau.goals:
    cost = max(cost,goal.expr.nodes())
  return cost

def select_tableau(frontier,complexity):
  penalty = list(map(lambda tab: complexity(tab[0]), frontier))
  idx = np.argmin(penalty)
  tableau,tableau_depth = frontier[idx]
  other_tableaus = list(map(lambda i: frontier[i], \
                            filter(lambda i: i != idx, \
                                   range(0,len(frontier)))))
  return tableau,tableau_depth,other_tableaus

def simplify_tableau(tableau,simplify_laws=False):
  new_tableau = tableau.copy()

  for goal in tableau.goals:
    if isinstance(goal.variable, PortVar) and \
       goal.expr.op == oplib.OpType.VAR:
      new_tableau.remove_goal(goal)
      new_tableau.add_stmt(VADPSink(goal.variable, \
                                    goal.expr))

  if simplify_laws:
    for rel in new_tableau.relations:
      if isinstance(rel,PhysicsLawRelation):
        new_vadp = rel.simplify(new_tableau.vadp)
        new_tableau.vadp = new_vadp

  return new_tableau

def is_concrete_vadp(vadp):
  for stmt in vadp:
    if isinstance(stmt,VADPSink) or \
       isinstance(stmt,VADPSource):
      if not isinstance(stmt.port,PortVar):
        return False

    elif isinstance(stmt,VADPConn):
      if not isinstance(stmt.source,PortVar) or \
         not isinstance(stmt.sink,PortVar):
        return False
    elif isinstance(stmt,VADPConfig):
      pass
    else:
      raise Exception("unhandled: %s" % stmt)

  return True

def search(blocks,laws,variable,expr,depth=20):
  tableau = make_initial_tableau(blocks,laws, \
                                 variable,expr)

  frontier = [(tableau,0)]

  next_frontier = []
  valid_tableaus = list(get_valid_tableaus(frontier,depth))
  solutions = 0
  while len(valid_tableaus) > 0:
    tableau,tab_depth,other_tableaus = select_tableau(valid_tableaus, \
                                                      tableau_complexity)
    next_frontier = other_tableaus
    goal = tableau.goals[0]
    for new_tableau in derive_tableaus(tableau,goal):
      simpl_tableau = simplify_tableau(new_tableau)
      if simpl_tableau.success():
        simpl_tableau = simplify_tableau(new_tableau, \
                                         simplify_laws=True)
        assert(is_concrete_vadp(simpl_tableau.vadp))
        yield simpl_tableau.vadp
        solutions += 1
      else:
        next_frontier.append((simpl_tableau,tab_depth + 1))

    valid_tableaus = list(get_valid_tableaus(next_frontier,depth))

  print("Solutions for <%s=%s>: %d" % (variable,expr,solutions))

