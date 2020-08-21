import compiler.lscale_pass.lscale_problem as lscaleprob
import compiler.lscale_pass.lscale_ops as scalelib
import compiler.lscale_pass.lscale_solver as lscale_solver

def get_objective():
  qual = scalelib.QualityVar()

  monom = scalelib.SCMonomial()
  monom.add_term(qual,-1.0)
  return monom

def scale(dev, program, adp):
  cstr_prob = []
  for stmt in lscaleprob. \
      generate_constraint_problem(dev,program,adp):
    cstr_prob.append(stmt)

  obj = get_objective()
  for adp in lscale_solver.solve(dev,adp,cstr_prob,obj):
    for cfg in adp.configs:
      assert(cfg.complete())

    yield adp

