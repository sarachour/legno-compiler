import compiler.lscale_pass.lscale_problem as lscaleprob
import compiler.lscale_pass.lscale_ops as scalelib
import compiler.lscale_pass.lscale_solver as lscale_solver
import hwlib.adp as adplib

def get_objective(objective,cstr_prob):
  aqm= scalelib.QualityVar(scalelib.QualityMeasure.AQM)
  dqm= scalelib.QualityVar(scalelib.QualityMeasure.DQM)
  dqme= scalelib.QualityVar(scalelib.QualityMeasure.DQME)
  aqmst= scalelib.QualityVar(scalelib.QualityMeasure.AQMST)
  aqmobs = scalelib.QualityVar(scalelib.QualityMeasure.AQMOBS)
  timescale = scalelib.TimeScaleVar()

  all_vars = []
  for cstr in cstr_prob:
    all_vars += list(map(lambda v: str(v), cstr.vars()))

  quality_vars = list(filter(lambda v: str(v) in all_vars, \
                             [aqm,dqm,dqme,aqmst,aqmobs]))

  if scalelib.ObjectiveFun.QUALITY == objective:
    monom = scalelib.SCMonomial()
    for qv in quality_vars:
      monom.add_term(qv,-1.0)
    return monom

  elif scalelib.ObjectiveFun.QUALITY_SPEED == objective:
    monom = scalelib.SCMonomial()
    for qv in quality_vars:
      monom.add_term(qv,-0.5)
    monom.add_term(timescale,-1)
    return monom

  elif scalelib.ObjectiveFun.SPEED == objective:
    monom = scalelib.SCMonomial()
    monom.add_term(timescale,-1)
    return monom

  else:
    raise Exception("unknown objective: %s" % objective)

def adp_summary(adp):
  templ = ["=========", \
           "Method: {method}", \
           "Objective: {objective}", \
           "AQM:   {aqm}", \
           "AQMST: {aqmst}", \
           "AQMOBS: {aqmobs}", \
           "DQM:   {dqm}", \
           "DQME:  {dqme}", \
           "TAU:   {tau}"]

  args = {
    'tau':adp.tau,
    'aqm':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_AQM),
    'aqmobs':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_AQMOBS) \
    if adp.metadata.has(adplib.ADPMetadata.Keys.LSCALE_AQMOBS) else "<don't care>",
    'aqmst':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_AQMST) \
    if adp.metadata.has(adplib.ADPMetadata.Keys.LSCALE_AQMST) else "<don't care>",
    'dqm':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_DQM),
    'dqme': adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_DQME)  \
    if adp.metadata.has(adplib.ADPMetadata.Keys.LSCALE_DQME) else "<don't care>",
    'method':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD),
    'objective':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE),
  }
  st = ""
  for stmt in templ:
    st += "%s\n" % (stmt.format(**args))
  return st

def scale(dev, program, adp, \
          objective=scalelib.ObjectiveFun.QUALITY, \
          scale_method=scalelib.ScaleMethod.IDEAL, \
          calib_obj=None, \
          no_scale=False, \
          one_mode=False):

  def set_metadata(adp):
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                     scale_method.value)
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE, \
                           objective.value)
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_NO_SCALE, \
                     no_scale)
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_ONE_MODE, \
                     one_mode)
    adp.metadata.set(adplib.ADPMetadata.Keys.RUNTIME_CALIB_OBJ, \
                           calib_obj.value)
    adp.metadata.set(adplib.ADPMetadata.Keys.RUNTIME_PHYS_DB, \
                           dev.model_number)


  cstr_prob = []
  for stmt in lscaleprob. \
      generate_constraint_problem(dev,program,adp, \
                                  scale_method=scale_method, \
                                  calib_obj=calib_obj, \
                                  one_mode=one_mode, \
                                  no_scale=no_scale):
    cstr_prob.append(stmt)

  obj = get_objective(objective,cstr_prob)

  if scale_method == scalelib.ScaleMethod.NOSCALE:
    for cfg in adp.configs:
      cfg.modes = [cfg.modes[0]]

    set_metadata(adp)
    yield adp
    return

  for adp in lscale_solver.solve(dev,adp,cstr_prob,obj):
    set_metadata(adp)
    for cfg in adp.configs:
      assert(cfg.complete())

    print(adp_summary(adp))
    yield adp

