import compiler.lscale_pass.lscale_problem as lscaleprob
import compiler.lscale_pass.lscale_ops as scalelib
import compiler.lscale_pass.lscale_solver as lscale_solver
import hwlib.adp as adplib
import util.paths as paths
import numpy as np
import math

import os
import json
# return top 
def metadata_matches(adp1,adp2,keys):
  for key in keys:
    if adp1.metadata.get(key) != adp2.metadata.get(key):
      return False
  return True

# get the relevent scaling factors if there have already been executiosn
def get_relevent_scaling_factors(dev,adp,top=5):
    if adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE) != scalelib.ObjectiveFun.EMPIRICAL.value:
       return

    ph = paths.PathHandler('unrestricted', \
                                     adp.metadata.get(adplib.ADPMetadata.Keys.DSNAME))

    rmses = []
    variables = {}
    scfs = {}
    for dirname, subdirlist, filelist in \
        os.walk(ph.lscale_adp_dir()):
      for adp_file in filelist:
        if adp_file.endswith('.adp'):
          with open(dirname+"/"+adp_file,'r') as fh:
            curr_adp_json = json.loads(fh.read())
            curr_adp = adplib.ADP.from_json(dev, curr_adp_json)
            if metadata_matches(curr_adp,adp,[ \
                                               adplib.ADPMetadata.Keys.LGRAPH_ID, \
                                               adplib.ADPMetadata.Keys.RUNTIME_CALIB_OBJ, \
                                               adplib.ADPMetadata.Keys.LSCALE_ONE_MODE, \
                                               adplib.ADPMetadata.Keys.LSCALE_NO_SCALE, \
                                               adplib.ADPMetadata.Keys.RUNTIME_PHYS_DB
            ]):
              if not curr_adp.metadata.has(adplib.ADPMetadata.Keys.LWAV_NRMSE):
                continue

              rmses.append(curr_adp.metadata.get(adplib.ADPMetadata.Keys.LWAV_NRMSE))
              for cfg in curr_adp.configs:
                blk = dev.get_block(cfg.inst.block)
                for stmt in cfg.stmts:
                  if stmt.type == adplib.ConfigStmtType.CONSTANT or \
                     stmt.type == adplib.ConfigStmtType.PORT:
                   varb =  scalelib.PortScaleVar(cfg.inst, stmt.name)
                   if not str(varb) in variables:
                     variables[str(varb)] = varb
                     scfs[str(varb)] = []
                   scfs[str(varb)].append(stmt.scf)


              print(adp_file)

    correlations = []
    variable_names = list(variables.keys())
    if len(variable_names) == 0:
      raise Exception("cannot use empirical scale objective. None of the existing executions have been analyzed.")

    for var_name in variable_names:
      coeff = np.corrcoef(rmses,scfs[var_name])[0][1]
      if math.isnan(coeff):
        coeff = 0.0

      correlations.append(coeff)


    scores = list(-1.0*np.abs(np.array(correlations)))
    indices = np.argsort(scores)
    for idx in indices[0:min(top,len(indices))]:
      print(correlations[idx])
      sign = 1.0 if correlations[idx] >= 0.0 else -1.0
      varname = variable_names[idx]
      yield sign,variables[varname]





def get_objective(objective,cstr_prob,relevent_scale_factors=[]):
  aqm= scalelib.QualityVar(scalelib.QualityMeasure.AQM)
  dqm= scalelib.QualityVar(scalelib.QualityMeasure.DQM)
  dqme= scalelib.QualityVar(scalelib.QualityMeasure.DQME)
  aqmst= scalelib.QualityVar(scalelib.QualityMeasure.AQMST)
  aqmobs = scalelib.QualityVar(scalelib.QualityMeasure.AQMOBS)
  #avgaqm = scalelib.QualityVar(scalelib.QualityMeasure.AVGAQM)
  #avgdqm = scalelib.QualityVar(scalelib.QualityMeasure.AVGDQM)
  timescale = scalelib.TimeScaleVar()
  expos = {}
  expos[aqm] = 1.0
  expos[dqm] = 1.0
  expos[dqme] = 1.0
  expos[aqmst] = 1.0
  #expos[avgaqm] = 1.0
  #expos[avgdqm] = 1.0
  expos[aqmobs] = 1.0


  all_vars = []
  for cstr in cstr_prob:
    all_vars += list(map(lambda v: str(v), cstr.vars()))

  #all_quality_vars = [avgaqm,avgdqm,aqm,dqm,dqme,aqmst,aqmobs]
  all_quality_vars = [aqm,dqm,dqme,aqmst,aqmobs]
  quality_vars = list(filter(lambda v: str(v) in all_vars, \
                             all_quality_vars))

  if scalelib.ObjectiveFun.QUALITY == objective:
    monom = scalelib.SCMonomial()
    for qv in quality_vars:
      monom.add_term(qv,-expos[qv])
    return monom

  elif scalelib.ObjectiveFun.RANDOM == objective:
    return None

  elif scalelib.ObjectiveFun.ANALOG_QUALITY_ONLY == objective:
    all_quality_vars = [aqm,dqme,aqmobs]
    quality_vars = list(filter(lambda v: str(v) in all_vars, \
                             all_quality_vars))

    monom = scalelib.SCMonomial()
    for qv in quality_vars:
      monom.add_term(qv,-expos[qv])
    return monom


  elif scalelib.ObjectiveFun.EMPIRICAL == objective:
    monom = scalelib.SCMonomial()
    for qv in quality_vars:
      monom.add_term(qv,-expos[qv])
    monom.add_term(timescale,-1)
    for sign,scf in relevent_scale_factors:
      monom.add_term(scf,sign*-1.0)

    return monom


    raise Exception("not implemented error")
  elif scalelib.ObjectiveFun.QUALITY_SPEED == objective:
    monom = scalelib.SCMonomial()
    for qv in quality_vars:
      monom.add_term(qv,-expos[qv])
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
           "AVG AQM: {avg_aqm}", \
           "DQM:   {dqm}", \
           "AVG DQM: {avg_dqm}", \
           "AQMST: {aqmst}", \
           "AQMOBS: {aqmobs}", \
           "DQME:  {dqme}", \
           "TAU:   {tau}"]

  args = {
    'tau':adp.tau,
    'aqm':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_AQM),
    'avg_aqm':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_AVGAQM)
    if adp.metadata.has(adplib.ADPMetadata.Keys.LSCALE_AVGAQM) else "<don't care>",
    'avg_dqm':adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_AVGDQM)
    if adp.metadata.has(adplib.ADPMetadata.Keys.LSCALE_AVGDQM) else "<don't care>",
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


  set_metadata(adp)
  scfs = list(get_relevent_scaling_factors(dev,adp))
  cstr_prob = []
  for stmt in lscaleprob. \
      generate_constraint_problem(dev,program,adp, \
                                  scale_method=scale_method, \
                                  calib_obj=calib_obj, \
                                  one_mode=one_mode, \
                                  no_scale=no_scale):
    cstr_prob.append(stmt)

  obj = get_objective(objective,cstr_prob,scfs)

  print("<<< solving >>>")
  for adp in lscale_solver.solve(dev,adp,cstr_prob,obj):
    set_metadata(adp)
    for cfg in adp.configs:
      assert(cfg.complete())

    print(adp_summary(adp))
    yield adp
    print("<<< solving >>>")

