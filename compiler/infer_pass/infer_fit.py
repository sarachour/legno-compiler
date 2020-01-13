import compiler.infer_pass.infer_util as infer_util
import util.util as util
import compiler.infer_pass.infer_visualize as infer_vis
from sklearn import svm
from sklearn.metrics import r2_score

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp2d
import scipy.optimize
import math
import sklearn.tree as tree
from scipy import stats


DISABLE_BLOCKS = True

def remove_outliers(model,in0,in1,classes):
  def test(x,l,u):
    return x <= u and l <= x

  def error(cls,pred):
    if not cls and pred:
      return 1.0
    elif cls and not pred:
      return 0.2
    else:
      return 0.0

  def cost(pars):
    l0,u0,l1,u1 = pars
    n = len(in0)
    preds = list(map(lambda i: \
                      test(in0[i],l0,u0) and \
                      test(in1[i],l1,u1),
                      range(n)))

    score = sum(map(lambda i: \
                    error(classes[i],preds[i]), range(n)))
    return score

  scf = 0.95
  bounds = [
    (min(in0),min(in0)*scf),
    (max(in0)*scf,max(in0)),
    (min(in1),min(in1)*scf),
    (max(in1)*scf,max(in1)),
  ]
  result = scipy.optimize.brute(cost, bounds, \
                                finish=scipy.optimize.fmin,
                                Ns=5)

  clipped = []
  for (l,u),r in zip(bounds,result):
    cr = min(max(l,r),u)
    clipped.append(cr)
  return (clipped[0],clipped[1]),(clipped[2],clipped[3])

def get_outlier_classifier(error):
  Q1 = np.percentile(error, 25)
  Q3 = np.percentile(error, 75)
  IQR = Q3-Q1
  UB = IQR+Q3
  # we only care about the upper bound
  return UB

def plot_error_distribution(model,error,cutoff):
  if not infer_vis.DO_PLOTS:
    return

  avg_error = np.mean(error)
  std_error = np.std(error)

  plt.hist(error, normed=True, bins=30)
  plt.axvline(x=cutoff,c="red")
  filename = infer_vis.get_plot_name(model,'edist')
  plt.savefig(filename)
  plt.clf()

def plot_outlier(model,in0,in1,errors,cutoff):
  colors = list(map(lambda e: "green" if e <= cutoff else "red", errors))
  plt.scatter(in0,in1,c=colors)
  filename = infer_vis.get_plot_name(model,'outlier')
  plt.savefig(filename)
  plt.clf()

def split_model(model,dataset,max_unc):
  meas,out = dataset.meas,dataset.out
  in0,in1 = dataset.in0,dataset.in1
  n = dataset.n
  assert(n > 0)
  pred = util.apply_model(model,out)
  err = util.array_map(map(lambda i: abs(pred[i]-meas[i]), range(n)))
  adapt_err = get_outlier_classifier(err)
  plot_error_distribution(model,err,adapt_err)
  plot_outlier(model,in0,in1,err,adapt_err)
  classes = list(map(lambda i: err[i] <= adapt_err,range(n)))
  (in0l,in0h),(in1l,in1h)= remove_outliers(model,in0,in1,classes)
  dataset.set_bounds(in0l,in0h,in1l,in1h)






class InferDataset:

  def __init__(self,in0,in1,out,bias,noise):
    self.fields = {}
    self.indices = list(range(len(in0)))
    self.fields = ['in0','in1','out','noise','meas']
    self._in0 = in0
    self._in1 = in1
    self._out = out
    self._noise = noise
    self._meas = list(map(lambda i: bias[i]+out[i], \
                          self.indices))
    self._in0_bnd = (None,None)
    self._in1_bnd = (None,None)

  def _get_datum(self,key):
    return util.array_map(map(lambda i: self.__dict__[key][i],  \
                         self.indices))

  @property
  def n(self):
    return len(self.indices)

  @property
  def in0(self):
    return self._get_datum('_in0')


  @property
  def in1(self):
    return self._get_datum('_in1')


  @property
  def out(self):
    return self._get_datum('_out')

  @property
  def noise(self):
    return self._get_datum('_noise')

  @property
  def meas(self):
    return self._get_datum('_meas')

  def set_bounds(self,in0l,in0h,in1l,in1h):
    def in_bounds(v,l,h):
      return v >= l \
        and v <= h
    self._in0_bnd = (in0l,in0h)
    self._in1_bnd = (in1l,in1h)
    self.indices = list(filter(lambda i: \
                            in_bounds(self._in0[i],in0l,in0h) and \
                            in_bounds(self._in1[i],in1l,in1h), \
                            range(len(self._in0))))

  @property
  def in0_bounds(self):
    return self._in0_bnd

  @property
  def in1_bounds(self):
    return self._in1_bnd

MIN_RSQ = 0.95

def denormalize_values(model,data):
  if model.block == "multiplier" or \
     model.block == "integrator" or \
     model.block == "tile_dac" or \
     model.block == "fanout":
    return list(map(lambda d: 2.0*d, data))
  else:
    return data

def fit_vga_model(model,dataset):
  in0,in1,observe,expect= dataset.in0,dataset.in1,dataset.meas,dataset.out
  n = dataset.n

  inds = filter(lambda i: expect[i] != 0.0, range(0,n))
  coeff = np.mean(np.array(list(map(lambda i: expect[i]/(in0[i]*in1[i]), \
                                    inds))))

  def func(xs,a,b,c):
    x = xs[0]
    y = xs[1]
    return coeff*(x*a+b)*y + c

  min_pts = 10
  if n < min_pts:
    print(model)
    input("not enough points: %d" % n)
    return

  popt, pcov = scipy.optimize.curve_fit(func, [in1,in0], observe)
  gain = popt[0]
  gain_offset = popt[1]
  bias = popt[2]
  rsq = r2_score(observe, func([in1,in0],gain,gain_offset,bias))

  pred = list(map(lambda i: func([in1[i],in0[i]], \
                                 gain,gain_offset,bias), \
                  range(n)))
  errs = list(map(lambda i : observe[i]-pred[i], range(n)))
  print("eqn: (%f*(gain+%f))*sig+%f" % (gain,gain_offset/gain,bias))
  print("r-squared=%f" % rsq)
  stderr = np.mean(np.abs(errs))
  print("stderr=%f" % (stderr))
  if abs(rsq) < MIN_RSQ:
    print("==========")
    print(model)
    model.gain_offset = 0.0
    print("Skipping: rval=%f error=%f" % (rsq,stderr))
    return True if stderr <= 0.01 else False


  model.gain = gain
  model.bias = bias
  model.gain_offset = (gain_offset/gain)
  model.bias_uncertainty.from_data(errs, \
                                   denormalize_values(model,pred))

  # only accept models with bias and variance
  # below some threshold.
  if np.std(errs) <= max_stderr(dataset.out) and \
    np.mean(errs) <= max_stderr(dataset.out):
    return True
  else:
    return False


def fit_affine_model(model,dataset):
  def func(x,a,b):
    return x*a+b

  def error(x,xhat,a,b):
    return abs(func(x,a,b)-xhat)

  min_pts = 10
  n = dataset.n
  observe,expect = dataset.meas,dataset.out
  if n < min_pts:
    print(model)
    input("not enough points: %d" % n)
    return

  slope,intercept,rval,pval,stderr = scipy.stats.linregress(expect,observe)
  pred = np.array(list(map(lambda e: slope*e+intercept, \
                           expect)))
  errors = np.array(list(map(lambda i: observe[i] - pred[i], \
                             range(0,n))))

  if abs(rval) < MIN_RSQ:
    print("==========")
    print(model)
    print(" gain=%f" % slope);
    print(" bias=%f" % intercept);
    print("Skipping: rval=%f error=%f" % (rval,stderr))
    return True if stderr <= 0.005 else False

  model.gain = slope
  model.bias = intercept
  model.bias_uncertainty.from_data(errors, \
                                   denormalize_values(model,pred))
  # only accept models with bias and variance
  # below some threshold.
  if intercept <= max_stderr(expect) and \
    model.bias_uncertainty.average <= max_stderr(expect):
    return True
  else:
    return False

def max_stderr(pts):
  if max(abs(pts)) > 3.0:
    return 0.2
  else:
    return 0.02

def fit_linear_model(model,dataset):
  def func(x,a):
    return x*a

  def error(x,xhat,a):
    return func(x,a)-xhat

  min_pts = 10
  n = dataset.n
  if n < min_pts:
    print(model)
    input("not enough points: %d" % n)
    return

  bias = observe-expect;
  popt, pcov = scipy.optimize.curve_fit(func, expect, observe)
  gain_mu = popt[0]
  rsq = r2_score(bias, func(expect,gain_mu))
  errs = list(map(lambda i : error(expect[i], \
                                   observe[i],
                                   gain_mu), range(n)))
  print("r-squared=%f" % rsq)
  stderr = np.std(errs)
  if abs(rsq) < MIN_RSQ:
    print("==========")
    print(model)
    print(" gain=%f" % gain_mu);
    print("Skipping: rval=%f error=%f" % (rsq,stderr))
    return True if stderr <= 0.01 else False



  model.gain = gain_mu
  model.gain_uncertainty.maximum = 0.0
  model.gain_uncertainty.average = 0.0
  model.bias = 0.0
  model.bias_uncertainty.maximum = max(abs(max(errs)),abs(min(errs)))
  model.bias_uncertainty.average = np.mean(abs(errs))

  # only accept models with bias and variance
  # below some threshold.
  if np.std(errs) <= max_stderr(expect) and \
    np.mean(errs) <= max_stderr(expect):
    return True
  else:
    return False

def infer_model(model,in0,in1,out,bias,noise, \
                uncertainty_limit, \
                adc=False,
                required_points=20,
                kind="affine"):


  dataset = InferDataset(in0,in1,out,bias,noise)
  cnt =0
  max_prune = 0
  print(kind)
  while True:
    if kind == "affine":
      success = fit_affine_model(model,dataset)
    elif kind == "vga":
      success = fit_vga_model(model,dataset)
    elif kind == "linear":
      success = fit_linear_model(model,dataset)
    else:
      raise Exception("unknown")

    if DISABLE_BLOCKS:
      model.enabled = success
    else:
      model.enabled = True

    model.noise = math.sqrt(np.mean(dataset.noise))
    if cnt < max_prune and dataset.n >= required_points:
      split_model(model, \
                  dataset, \
                  uncertainty_limit)
      cnt += 1
    else:
      l0,u0 = dataset.in0_bounds
      l1,u1 = dataset.in1_bounds
      return dataset, {
        'in0': dataset.in0_bounds,
        'in1': dataset.in1_bounds
      }

def build_model(model,dataset,mode,max_uncertainty,adc=False,kind="affine"):
  bias,noise,in0,in1,out = infer_util \
                           .get_data_by_mode(dataset,mode)
  dataset,bnd= infer_model(model,in0,in1,out, \
                           bias,noise,max_uncertainty,adc=adc,kind=kind)

  infer_vis.plot_error(model,\
                       infer_vis.get_plot_name(model,'nodelta-error'), \
                       dataset, \
                       use_delta_model=False,
                       adc=adc)
  # none can be bnd
  infer_vis.plot_error(model, \
                       infer_vis.get_plot_name(model,'delta-error'), \
                       dataset, \
                       use_delta_model=True,
                       adc=adc)
  plt.close('all')
  return bnd
