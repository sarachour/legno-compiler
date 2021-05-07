import compiler.lscale_pass.lscale_problem as lscaleprob
import compiler.lscale_pass.lscale_ops as scalelib
import compiler.lscale_pass.lscale_solver as lscale_solver
import hwlib.adp as adplib
import util.paths as paths
import numpy as np
import math
import random

import os
import json
# return top 
def metadata_matches(adp1,adp2,keys):
  for key in keys:
    if adp1.metadata.get(key) != adp2.metadata.get(key):
      return False
  return True


def random_objectives(cstr_prob,count):
  all_vars = []
  var_map = {}
  skipped_blocks = ['tin','tout']
  for cstr in cstr_prob:
    for var in cstr.vars():
      if isinstance(var,scalelib.PortScaleVar) and \
         not var.inst.block in skipped_blocks:
         var_map[(var.inst,var.port)] = var
      elif isinstance(var,scalelib.TimeScaleVar):
         var_map["speed"] = var

  all_vars = list(var_map.values())
  print("===========================")
  print("TOTAL_VARIABLES: %d" % len(all_vars))
  print("===========================")
  for idx in range(min(count,len(all_vars))):
    monom = scalelib.SCMonomial()
    variables = [all_vars[idx]]
    for var in variables:
      monom.add_term(var,-10.0)

    print("<<< Variable %d/%d (%s) >>>" % (idx,len(all_vars),var))
    yield monom



def get_objective(objective,cstr_prob):
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
    return None,[monom]

  elif scalelib.ObjectiveFun.RANDOM == objective:
    return 1,list(random_objectives(cstr_prob,1e6))


  elif scalelib.ObjectiveFun.QUALITY_SPEED == objective:
    monom = scalelib.SCMonomial()
    for qv in quality_vars:
      monom.add_term(qv,-expos[qv])
    monom.add_term(timescale,-1)
    return None,[monom]

  elif scalelib.ObjectiveFun.SPEED == objective:
    monom = scalelib.SCMonomial()
    monom.add_term(timescale,-1)
    return None,[monom]

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
          one_mode=False, \
          min_aqm=None, \
          min_dqm=None, \
          min_dqme=None, \
          min_tau=None):

  def set_metadata(adp,obj):
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                     scale_method.value)
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE, \
                           objective.value)
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE_EXPR, \
                           str(obj))
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_NO_SCALE, \
                     no_scale)
    adp.metadata.set(adplib.ADPMetadata.Keys.LSCALE_ONE_MODE, \
                     one_mode)
    adp.metadata.set(adplib.ADPMetadata.Keys.RUNTIME_CALIB_OBJ, \
                           calib_obj.value)
    adp.metadata.set(adplib.ADPMetadata.Keys.RUNTIME_PHYS_DB, \
                           dev.model_number)


  set_metadata(adp,"")
  cstr_prob = []
  for stmt in lscaleprob. \
      generate_constraint_problem(dev,program,adp, \
                                  scale_method=scale_method, \
                                  calib_obj=calib_obj, \
                                  one_mode=one_mode, \
                                  no_scale=no_scale, \
                                  min_aqm=min_aqm, \
                                  min_dqm=min_dqm, \
                                  min_dqme=min_dqme, \
                                  min_tau=min_tau):
    cstr_prob.append(stmt)

  max_solutions,obj = get_objective(objective,cstr_prob)

  print("<<< solving >>>")
  for objfun,adp in lscale_solver.solve(dev,adp,cstr_prob,obj,max_solutions=max_solutions):
    set_metadata(adp,objfun)
    for cfg in adp.configs:
      assert(cfg.complete())

    print(adp_summary(adp))
    yield adp
    print("<<< solving >>>")

