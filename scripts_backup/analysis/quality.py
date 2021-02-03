import numpy as np
from scipy import stats
import math
import time
import json
import util.paths as paths
from scipy import optimize
import util.util as util
import matplotlib.pyplot as plt
from scipy import signal, fftpack
import scripts.analysis.common as common

import dslang.dsprog as dsproglib
CACHE = {}

def scale_obs_data(output,tobs,yobs,scale_time=True):
  transform = output.transform
  time_scale = 1.0/(transform.legno_time_scale \
                    *transform.time_constant)
  exp_time_scale = transform.expd_time_scale
  exp_time_offset = transform.expd_time_offset
  val_scale = transform.legno_ampl_scale
  if scale_time:
    trec = list(map(lambda t: (t-exp_time_offset)/(time_scale/exp_time_scale), \
                    tobs))
  else:
    trec = list(tobs)

  yrec = list(map(lambda x: x/val_scale, yobs))
  tmin = 0
  tmax = output.runtime/time_scale
  inds = list(filter(lambda i: trec[i] <= tmax and trec[i] >= tmin, \
                     range(len(trec))))
  trec_trim = util.array_map(map(lambda i: trec[i],inds))
  yrec_trim = util.array_map(map(lambda i: yrec[i],inds))
  return trec_trim, yrec_trim


def scale_ref_data(output,tref,yref):
  transform = output.transform
  time_scale = 1.0/(transform.legno_time_scale \
                    *transform.time_constant)
  time_offset = 0.0
  val_scale = transform.legno_ampl_scale
  thw = list(map(lambda t: t*time_scale+time_offset, tref))
  yhw = list(map(lambda x: x*val_scale, yref))
  return thw, yhw


def compute_ref(progname,dssimname,variable):
  if not (progname,dssimname,variable) in CACHE:
    prog = dsproglib.DSProgDB.get_prog(progname)
    dssim = dsproglib.DSProgDB.get_sim(progname)
    if not (dssim.name == dssimname):
      raise Exception("not the same simulation: expected=%s given=%s" \
                      % (dssim.name,dssimname))
    T,D = prog.execute(dssim)
    TREF,YREF = T,D[variable]

    CACHE[(progname,dssimname,variable)] = (TREF,YREF)
    return TREF,YREF
  else:
      return CACHE[(progname,dssimname,variable)]

def read_meas_data(filename):
  with open(filename,'r') as fh:
    print(filename)
    obj = util.decompress_json(fh.read())
    T,V = obj['times'], obj['values']
    T_REFLOW = np.array(T) - min(T)
    return T_REFLOW,V

def make_prediction(t_meas,x_meas,model):
    a,b,c,d = model
    t_pred = a*t_meas - b
    x_pred = c*x_meas - d
    return t_pred,x_pred

def compute_pct_nrmsd(ref_t,ref_x,pred_t,pred_x,debug=False):
  pred_x_reflow = np.interp(ref_t, pred_t, pred_x, left=0, right=0)
  # root mean squared error
  MSE = np.sum((pred_x_reflow-ref_x)**2)/len(ref_t)
  RMSD = math.sqrt(MSE)
  # root mean squared error relative to full scale
  FS = float(max(ref_x) - min(ref_x))
  NRMSD = RMSD/FS
  PCT_NRMSD = NRMSD*100.0
  if debug:
    print("MSE=%e" % MSE)
    print("RMSD=%e" % RMSD)
    print("FS=%e" % FS)
    print("NRMSD=%f" % NRMSD)
    print("PCT_NRMSD=%f" % PCT_NRMSD)
  return PCT_NRMSD


def lag_finder(t1,y1,t2,y2):
  n = 10000
  times = np.linspace(min(t1),max(t1),n)
  dt = np.mean(np.diff(times))
  y2_reflow= np.interp(times,t2,y2,left=0,right=0)
  y1_reflow= np.interp(times,t1,y1,left=0,right=0)
  corr = signal.correlate(y1_reflow,y2_reflow)
  offset = np.argmax(corr)
  t_delta = (offset-n)*dt
  return -t_delta

def fit(output,_tref,_yref,_tmeas,_ymeas):
  def out_of_bounds(bounds,result):
    new_result = []
    assert(len(bounds) == len(result))
    for (lb,ub),r in zip(bounds,result):
      if r < lb or r > ub:
        print("%s not in (%s,%s)" % (r,lb,ub))
      new_result.append(max(min(r,ub),lb))

    assert(len(new_result) == len(result))
    return new_result

  def apply_model_to_obs(pred_t,meas_t,meas_x,model):
    a,b,c,d = model
    '''
    tmin,tmax = (pred_t-b)/a
    inds = list(filter(lambda i: \
                       meas_t[i] <= tmax \
                       and meas_t[i] >= tmin, \
                       range(len(meas_t))))
    '''
    inds = list(range(len(meas_t)))
    rt = list(map(lambda i: a*meas_t[i]-b,inds))
    rx = list(map(lambda i: c*meas_x[i]-d, inds))
    return rt,rx

  tref = np.array(_tref)
  yref = np.array(_yref)
  tmeas = np.array(_tmeas)
  ymeas = np.array(_ymeas)
  #time_slack = 0.05
  time_slack = 0.02
  bounds = [
    (1.0-time_slack,1.0+time_slack),
    (0.0,max(tmeas)*0.1)
  ]
  def clamp(result,i):
    return min(max(result[i],bounds[i][0]),bounds[i][1])

  def compute_loss(x):
    model = [clamp(x,0),clamp(x,1),1.0,0]
    pred_t,pred_x = make_prediction(tmeas,ymeas,model)
    err = compute_pct_nrmsd(tref,yref,pred_t,pred_x)
    return err
  # apply transform to turn ref -> pred
  n = 15
  print("==== TRANSFORM ===")
  result = optimize.brute(compute_loss,bounds,Ns=n)
  #print(result)
  xform = output.transform
  #xform.expd_time_scale = 1.0
  xform.expd_time_scale = clamp(result,0)
  xform.expd_value_scale = 1.0
  xform.expd_time_offset = result[1]
  #xform.expd_time_offset = lag_finder(tref,yref,tmeas,ymeas)
  print("time-scale=%f (%f)" % (xform.expd_time_scale, result[0]))
  print("time-offset=%f" % (xform.expd_time_offset))
  print("value-scale=%f (%f)" % (xform.expd_value_scale, 1.0))
  print("========")
  # update database
  output.transform = xform

def compute_quality(output,_trec,_yrec,_tref,_yref):
  tref,yref= np.array(_tref), np.array(_yref)
  trec,yrec= np.array(_trec), np.array(_yrec)
  pct_nrmsd = compute_pct_nrmsd(tref,yref,trec,yrec, \
                                debug=True)

  plt.plot(trec,yrec)
  plt.plot(tref,yref)
  plt.savefig("debug.png")
  plt.clf()
  n = len(tref)
  if n == 0 or len(trec) == 0:
    return None,[],[]

  yobs_flow = np.interp(tref, trec, yrec, left=0, right=0)
  errors = np.array(list(map(lambda i: (yobs_flow[i]-yref[i])**2, range(n))))

  print("pct nrmsd: %s %%" % pct_nrmsd)
  return pct_nrmsd,tref,errors

def analyze(entry,recompute=False):
  path_h = paths.PathHandler(entry.subset,entry.program)
  QUALITIES = []
  VARS = set(map(lambda o: o.variable, entry.outputs()))
  MODEL = None
  dssim = dsproglib.DSProgDB.get_sim(entry.program)
  no_reference = (dssim.real_time)
  for output in entry.outputs():
    variable = output.variable
    trial = output.trial

    TMEAS,YMEAS = read_meas_data(output.waveform)
    common.simple_plot(output,path_h,output.trial,'meas',TMEAS,YMEAS)
    if no_reference:
      TFIT,YFIT = scale_obs_data(output,TMEAS,YMEAS,scale_time=False)
      common.simple_plot(output,path_h,output.trial,'rec',TFIT,YFIT)
      QUALITIES.append(0)
      continue

    #if not output.quality is None:
    #  QUALITIES.append(output.quality)

    TREF,YREF = compute_ref(entry.program,entry.dssim,variable)
    #common.simple_plot(output,path_h,output.trial,'ref',TREF,YREF)

    TPRED,YPRED = scale_ref_data(output,TREF,YREF)
    #common.simple_plot(output,path_h,output.trial,'pred',TPRED,YPRED)

    fit(output,TPRED,YPRED,TMEAS,YMEAS)
    TFIT,YFIT = scale_obs_data(output,TMEAS,YMEAS)

    if TFIT is None or YFIT is None:
      QUALITIES.append(-1)
      continue

    #common.simple_plot(output,path_h,output.trial,'rec',TFIT,YFIT)
    common.compare_plot(output,path_h,output.trial,'comp',TREF,YREF,TFIT,YFIT)
    RESULT = compute_quality(output,TFIT,YFIT,TREF,YREF)
    if RESULT == -1:
      QUALITIES.append(RESULT)
      continue

    QUALITY,TERR,YERR = RESULT
    if QUALITY is None:
      QUALITIES.append(-1)
      continue
    #common.simple_plot(output,path_h,output.trial,'err',TERR,YERR)
    output.quality = QUALITY
    QUALITIES.append(QUALITY)


  if len(QUALITIES) > 0:
    QUALITY = np.median(QUALITIES)
    entry.set_quality(QUALITY)
