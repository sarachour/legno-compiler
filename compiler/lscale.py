import compiler.lscale_pass.lscale_problem as lscaleprob
import compiler.lscale_pass.lscale_ops as scalelib
import compiler.lscale_pass.lscale_solver as lscale_solver
import hwlib.adp as adplib

def get_objective(objective):
  qual = scalelib.QualityVar()

  monom = scalelib.SCMonomial()
  monom.add_term(qual,-1.0)
  return monom

def scale(dev, program, adp, \
          objective=scalelib.ObjectiveFun.QUALITY, \
          scale_method=scalelib.ScaleMethod.IDEAL):

  cstr_prob = []
  for stmt in lscaleprob. \
      generate_constraint_problem(dev,program,adp):
    cstr_prob.append(stmt)

  obj = get_objective(objective)

  if scale_method == scalelib.ScaleMethod.NOSCALE:
    for cfg in adp.configs:
      cfg.modes = [cfg.modes[0]]

    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                     scale_method.value)
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE, \
                           objective.value)
    yield adp
    return

  for adp in lscale_solver.solve(dev,adp,cstr_prob,obj):
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                     scale_method.value)
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE, \
                           objective.value)
    for cfg in adp.configs:
      assert(cfg.complete())

    yield adp

