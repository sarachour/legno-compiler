import compiler.lgraph_pass.unify as unifylib
from compiler.lgraph_pass.tableau_data import *
import compiler.lgraph_pass.tableau_data as tablib
import ops.generic_op as genoplib

def cstrs_flip(variables):
  cstrs = dict(map(lambda v: (v,unifylib.UnifyConstraint.VARIABLE), \
                         variables))
  return cstrs

def apply_flip(goal,rule):
  law_var = tablib.LawVar(rule.law,rule.ident,tablib.LawVar.APPLY)
  if isinstance(goal.variable, tablib.PortVar):
    yield tablib.VADPSink(goal.variable,goal.expr)

  elif isinstance(goal.variable, tablib.DSVar):
    generic_var = GenericVar(goal.variable,rule.ident)
    yield tablib.VADPSink(generic_var,goal.expr)
    yield tablib.VADPSource(generic_var,genoplib.Var(goal.variable))

def simplify_flip(vadp_stmts,rule):
  return False,vadp_stmts

def cstrs_kirchoff(variables):
  cstrs = dict(map(lambda v: (v,unifylib.UnifyConstraint.NONE), \
                         variables))
  return cstrs

def apply_kirchoff(goal,rule):
  law_var = tablib.LawVar(rule.law,rule.ident,tablib.LawVar.APPLY)
  if isinstance(goal.variable, tablib.DSVar):
    var_name = goal.variable.var
    yield tablib.VADPSource(law_var,genoplib.Var(var_name))
  else:
    yield tablib.VADPConn(law_var,goal.variable)

def simplify_kirchoff(vadp_stmts,rule):
  target_var = None
  sink_stmt = None
  # identify statements with rule variables
  for stmt in vadp_stmts:
    if isinstance(stmt, VADPConn) and \
       isinstance(stmt.source, LawVar):
      sink_stmt = stmt
      sink_var = stmt.sink
      target_var = stmt.source
      break
    elif isinstance(stmt,VADPSource) and \
         isinstance(stmt.port, LawVar):
      sink_stmt = stmt
      sink_var = VirtualSourceVar(stmt.dsexpr.name)
      target_var = stmt.port
      break
  # is there is no statement with rule variables
  if sink_stmt is None:
    return False,vadp_stmts

  # identify sources that are linked to the same sink
  sources = []
  replaced_stmts = [sink_stmt]
  for stmt in vadp_stmts:
    if isinstance(stmt,VADPConn) and \
       isinstance(stmt.sink, LawVar) and \
       stmt.sink.same_usage(target_var):
      sources.append(stmt.source)
      replaced_stmts.append(stmt)

  if len(sources) == 0:
    return vadp_stmts

  new_vadp = []
  for source in sources:
    new_vadp.append(VADPConn(source,sink_var))

  if isinstance(sink_stmt,VADPSink):
    new_vadp.append(VADPSink(sink_var, \
                             sink_stmt.ds_var))
  elif isinstance(sink_stmt,VADPSource):
    new_vadp.append(VADPSource(sink_var, \
                               sink_stmt.dsexpr))

  for stmt in vadp_stmts:
    if not stmt in replaced_stmts:
      new_vadp.append(stmt)

  return True,new_vadp
