import compiler.lscale_pass.lscale_problem as lscaleprob
import compiler.lscale_pass.lscale_ops as scalelib
import compiler.lscale_pass.lscale_solver as lscale_solver
import hwlib.adp as adplib

def get_objective(objective):
  aqm= scalelib.QualityVar(scalelib.QualityMeasure.AQM)
  dqm= scalelib.QualityVar(scalelib.QualityMeasure.DQM)
  timescale = scalelib.TimeScaleVar()

  if scalelib.ObjectiveFun.QUALITY == objective:
    monom = scalelib.SCMonomial()
    monom.add_term(aqm,-1.0)
    monom.add_term(dqm,-1.0)
    return monom

  elif scalelib.ObjectiveFun.QUALITY_SPEED == objective:
    monom = scalelib.SCMonomial()
    monom.add_term(aqm,-1.0)
    monom.add_term(dqm,-1.0)
    monom.add_term(timescale)
    return monom

  elif scalelib.ObjectiveFun.SPEED == objective:
    monom = scalelib.SCMonomial()
    monom.add_term(timescale)
    return monom

  else:
    raise Exception("unknown objective: %s" % objective)

def adp_summary(adp):
  templ = ["=========", \
           "Method: {method}", \
           "Objective: {objective}", \
           "AQM: {aqm}", \
           "DQM: {dqm}", \
           "TAU: {tau}"]

  args = {
    'tau':adp.tau,
    'aqm':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_AQM),
    'dqm':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_DQM),
    'method':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD),
    'objective':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE),
  }
  st = ""
  for stmt in templ:
    st += "%s\n" % (stmt.format(**args))
  return st

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

    print(adp_summary(adp))
    yield adp

