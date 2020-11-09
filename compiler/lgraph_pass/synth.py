import hwlib.block as blocklib
import hwlib.device as devlib
import compiler.lgraph_pass.unify as unifylib
import compiler.lgraph_pass.vadp as vadplib
from compiler.lgraph_pass.tableau import *
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

  for law in laws:
    for mode,expr in law.virt.relations:
      lawvar = vadplib.LawVar(law.name, 0)
      rel = PhysicsLawRelation(law,lawvar,mode,expr)

    tab.add_relation(rel)

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

  block_var = vadplib.PortVar(rel.block,rel.ident)
  vadp_cfg = VADPConfig(block_var,rel.modes)
  for stmt in tableau.vadp:
    if isinstance(stmt,VADPConfig) and \
       stmt.same_target(vadp_cfg):
      stmt.merge(vadp_cfg)
      vadp_cfg = stmt

  data_vars = []
  for vop,e in unif.assignments:
    if rel.block.data.has(vop.name):
       dat = rel.block.data[vop.name]
       data_vars += [vop.name] + dat.inputs
       if dat.type == blocklib.BlockDataType.EXPR:
         repl = {}
         for block_var, ds_var in map(lambda inp: unif.get_by_name(inp), \
                                      dat.inputs):
           assert(ds_var.op == genoplib.OpType.VAR)
           repl[ds_var.name] = block_var

         assert(set(e.vars()) == set(repl.keys()))
         expr = e.substitute(repl)
         vadp_cfg.bind(vop.name,expr)
       else:
         vadp_cfg.bind(vop.name,e)


  # translate assignments to goals
  for vop,e in filter(lambda asgn: not asgn[0].name in data_vars, \
                      unif.assignments):
    v = vop.name
    # binding input port assignment
    if rel.block.inputs.has(v):
      sig_type = rel.block.inputs[v].type
      new_tableau.add_goal(Goal(PortVar(rel.block, \
                                        rel.ident, \
                                        rel.block.inputs[v]), \
                                sig_type,e))

    elif v in rel.cstrs and \
         rel.cstrs[v] == unifylib.UnifyConstraint.SAMEVAR:
      pass
    else:
      print(rel)
      print(rel.cstrs)
      print(rel.modes)
      raise Exception("unknown: %s=%s" % (v,e))

  new_tableau.add_stmt(vadp_cfg)

  # if we used a freshly generated block, make sure to replace it
  replenish_block = (rel.ident == max(map(lambda r: r.ident \
                                          if isinstance(r,PortRelation) \
                                          and r.same_block(rel) else 0, \
                                          tableau.relations)))

  # update existing relations in tableau to respect unification
  new_tableau.relations = []
  for curr_rel in tableau.relations:
    # find port relations using the same block
    if isinstance(curr_rel,PortRelation) and \
       curr_rel.same_block(rel)  \
       and curr_rel.ident == rel.ident:

      new_rel = curr_rel.copy()
      # do not add relation to new tableau
      if curr_rel.equals(rel):
        continue

      # could not concretize relation
      if not apply_vadp_config_to_relation(new_rel.block, \
                                           vadp_cfg, \
                                           unif, \
                                           new_rel):
        continue

      new_tableau.add_relation(new_rel)

    else:
      new_tableau.add_relation(curr_rel.copy())

  # add fresh block of same type if necessary
  if replenish_block:
    for output in rel.block.outputs:
      for expr,modes in output.relation.get_by_property():
        new_rel = PortRelation(rel.block,rel.ident+1,modes,output,expr)
        new_tableau.add_relation(new_rel)

  return new_tableau

def derive_tableau_from_phys_rel(tableau,goal,rel,unif):
  new_tableau = tableau.copy()
  new_tableau.remove_goal(goal)

  law = rel.law
  app_var = rel.target.make_law_var(law.virt.output.name)
  new_unif,stmts = law.apply(goal,rel,unif)
  for stmt in stmts:
    new_tableau.add_stmt(stmt)

  for law_var in law.virt.inputs:
    _,e = new_unif.get_by_name(law_var)
    new_tableau.add_goal(Goal(LawVar(rel.target.law, \
                                     rel.target.ident, \
                                     law_var), \
                              law.virt.get_type(law_var),e))

  for curr_rel in new_tableau.relations:
    if isinstance(curr_rel,PhysicsLawRelation) and \
       curr_rel.same_usage(rel):
      curr_rel.target.ident += 1


  return new_tableau

def compatible_relation(dev,goal,rel):
  goalvar = goal.variable

  if not rel.typecheck(goal):
    return False

  if isinstance(rel,PortRelation):
    # cannot use relation from the same block.
    if rel.same_block(goal.variable):
      return False

    if isinstance(goalvar,DSVar) and \
      not rel.port.type == blocklib.BlockSignalType.ANALOG:
      return False

    if isinstance(goalvar,PortVar) and \
       not devlib.path_exists(dev,rel.block.name,rel.port.name, \
                           goalvar.block.name,goalvar.port.name):
      return False

  return True

def derive_tableaus(dev,tableau,goal):
  for rel in tableau.relations:
    if not compatible_relation(dev,goal,rel):
      continue
    if isinstance(rel,PortRelation):
      for unif in unifylib.unify(rel.expr,goal.expr,rel.cstrs):
        new_tableau = derive_tableau_from_port_rel(tableau,goal,rel,unif)
        yield new_tableau

    elif isinstance(rel,PhysicsLawRelation):
      cstrs = rel.law.virt.unify_cstrs()
      print(rel.expr)
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

def tableau_complexity(tableau,depth):
  cost = 0.0
  for goal in tableau.goals:
    #cost += goal.expr.count()
    cost = max(goal.expr.count(),cost)
  return cost + len(tableau.goals) + depth

def goal_complexity(goal):
  return goal.expr.count()

def select_tableau(frontier,complexity):
  penalty = list(map(lambda tab: complexity(*tab), frontier))
  idx = np.argmin(penalty)
  tableau,tableau_depth = frontier[idx]
  other_tableaus = list(map(lambda i: frontier[i], \
                            filter(lambda i: i != idx, \
                                   range(0,len(frontier)))))
  return tableau,tableau_depth,other_tableaus

def select_goal(goals,complexity):
  penalty = list(map(lambda goal: complexity(goal), goals))
  idx = np.argmin(penalty)
  this_goal = goals[idx]
  other_goals = list(map(lambda i: goals[i], \
                            filter(lambda i: i != idx, \
                                   range(0,len(goals)))))
  return this_goal,other_goals

def simplify_tableau(tableau,simplify_laws=False):
  new_tableau = tableau.copy()

  # replace trivial goals of the form port=var with sinks
  for goal in tableau.goals:
    if (isinstance(goal.variable, PortVar) or \
        isinstance(goal.variable, LawVar)) and \
       goal.expr.op == oplib.OpType.VAR and \
       goal.type == blocklib.BlockSignalType.ANALOG:
      new_tableau.remove_goal(goal)
      new_tableau.add_stmt(VADPSink(goal.variable, \
                                    goal.expr))

  # perform simplification
  if simplify_laws:
    for rel in new_tableau.relations:
      if isinstance(rel,PhysicsLawRelation):
        new_vadp = rel.law.simplify(new_tableau.vadp)
        new_tableau.vadp = new_vadp

  return new_tableau

def search(dev,blocks,laws,variable,expr,depth=20):
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
    goal,other_goals = select_goal(tableau.goals, \
                       goal_complexity)
    print(">> %s" % goal)
    for g in other_goals:
      print("   %s" % g)
    print("------")

    for new_tableau in derive_tableaus(dev,tableau,goal):
      simpl_tableau = simplify_tableau(new_tableau)
      if simpl_tableau.success():
        simpl_tableau = simplify_tableau(new_tableau, \
                                         simplify_laws=True)
        if not is_concrete_vadp(simpl_tableau.vadp, \
                                allow_virtual=True):
          for stmt in simpl_tableau.vadp:
            print("  %s" % stmt)
          raise Exception("vadp tableau is not concrete!")

        yield simpl_tableau.vadp
        print(simpl_tableau)
        print("SUCCESS")
        solutions += 1
      else:
        next_frontier.append((simpl_tableau,tab_depth + 1))

    valid_tableaus = list(get_valid_tableaus(next_frontier,depth))
    print("number tableaus: %d" % len(valid_tableaus))

  print("Solutions for <%s=%s>: %d" % (variable,expr,solutions))

