import compiler.lgraph_pass.unify as unifylib
import compiler.lgraph_pass.tableau_data as tablib

def apply_kirchoff(goal,rule):
  law_var = tablib.LawVar(rule.law,rule.ident,tablib.LawVar.APPLY)
  if isinstance(goal.variable, tablib.DSVar):
    yield tablib.VADPSink(goal.variable,law_var)
  else:
    yield tablib.VADPConn(law_var,goal.variable)

def simplify_kirchoff(vadp_stmts):
  for stmt in vadp_stmts:
    print(stmt)
  raise NotImplementedError
