import numpy as np
import scipy.optimize

def clamp(v):
  return max(min(v,1.0),-1.0)

def logit(x):
  return x/(1-x)

def logit_to_prob(x):
  odds = np.exp(x)
  prob = odds/(1+odds)
  return prob

class ActiveLearner:

  def __init__(self):
    self._alpha_bounds = (0.5,1.5)
    self._beta_bounds = (-0.05,0.05)
    self._n_models = 100
    self._assembly = []
    for _ in range(self._n_models):
      lb,ub = self._alpha_bounds
      alpha = np.random.uniform(lb,ub)
      lb,ub = self._beta_bounds
      beta = np.random.uniform(lb,ub)
      self._assembly.append((alpha,beta))

    self._ideal = []
    self._observed= []

  def add_point(self,ideal,obs):
    self._ideal.append(ideal)
    self._observed.append(obs)

  def prob_model(self,alpha,beta):
    if len(self._ideal) == 0:
      return 1.0

    pred = map(lambda x: x*alpha+beta,self._ideal)
    errors = map(lambda args: (self._observed[args[0]]-args[1])**2, \
                enumerate(pred))
    error = sum(errors)/len(self._observed)
    value = 1.0-(error)
    if value < 0.0 or value > 1.0:
      print(value)
      input()
    prob = logit_to_prob(logit(value))
    return prob

  def prob_observed(self,alpha,beta,ideal,observation):
    pred = alpha*beta+ideal
    error = abs(pred-observation)
    value = 1.0 - (error/0.7)
    if value < 0.0 or value > 1.0:
      print(error)
      input()

    prob = logit_to_prob(logit(error))
    return prob

  def get_entropy(self,ideal):
    probs = []
    a_lb,a_ub = self._alpha_bounds
    b_lb,b_ub = self._beta_bounds
    obs_lower = clamp(a_lb*ideal+b_lb)
    obs_upper = clamp(a_ub*ideal+b_ub)
    observations = np.arange(obs_lower,obs_upper,0.01)
    probs = list(map(lambda i: 0.0, range(len(observations))))
    for alpha,beta in self._assembly:
      pmodel = self.prob_model(alpha,beta)
      for i,obs in enumerate(observations):
        pobs = self.prob_observed(alpha,beta,ideal,obs)
        probs[i] += pobs*pmodel


    entropy = -sum(map(lambda p: p*np.log(p),probs))
    return entropy

  def fit(self):
    def apply_params(xdata,a,b):
      x = xdata
      result = (a)*(x) + b
      return result

    (gain,offset),corrs= scipy \
                       .optimize.curve_fit(apply_params, \
                                           self._ideal, \
                                           self._observed)

    print("best gain=%f offset=%f" % (gain,offset))

  def choose_output(self):
    points = list(filter(lambda pt: not pt in self._ideal, \
                         np.linspace(-1.0,1.0,200)))
    entropies = list(map(lambda i: 0.0, range(len(points))))
    for i,pt in enumerate(points):
      entropies[i]= self.get_entropy(pt)

    i = np.argmax(entropies)
    return points[i]

alpha_known = 1.25
bias_known = 0.01

def gen_obs(ideal):
  det = alpha_known*ideal+bias_known
  nz = np.random.uniform(-0.03,0.03)
  return det+nz

learn = ActiveLearner()
iter = 0
while True:
  pt = learn.choose_output()
  print(pt)
  learn.add_point(pt,gen_obs(pt))
  if iter >= 2:
    learn.fit()

  iter += 1
  input()
