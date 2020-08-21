from scipy.integrate import ode
import compiler.lsim_pass.buildsim as buildsim
from dslang.dsprog import DSProgDB
import hwlib.adp as adplib
import tqdm
import numpy as np
import matplotlib.pyplot as plt

class ADPSimResult:

  def __init__(self,sim):
    self.sim = sim
    self.state_vars = list(sim.state_variables())
    self.values = {}
    for var in self.state_vars:
      self.values[var.key] = []
    self.time = []

  @property
  def num_vars(self):
    return len(self.state_vars)


  def data(self,state_var,rectify=True):
    assert(isinstance(state_var,buildsim.ADPSim.Var))
    vals = self.values[state_var.key]
    times = self.time
    scale_factor = self.sim.scale_factor(state_var)
    V = np.array(vals)/scale_factor
    T = np.array(times)/ self.sim.time_scale
    return T,V

  def add_point(self,t,xs):
    assert(len(xs) == len(self.state_vars))
    self.time.append(t)
    for var,val in zip(self.state_vars,xs):
      self.values[var.key].append(val)


def next_state(sim,values):
  vdict = dict(zip(map(lambda v: "%s" % v.var_name, \
                       sim.state_variables()),values))
  vdict['np'] = np
  result = [0.0]*len(sim.state_variables())
  for idx,v in enumerate(sim.state_variables()):
    result[idx] = eval(sim.derivative(v),vdict)

  return result


def run_adp_simulation(dev, \
                       dssim, \
                       sim):
  state_vars = list(sim.state_variables())

  def dt_func(t,vs):
    return next_state(sim,vs)

  time = dssim.sim_time/(sim.time_scale)
  n = 300.0
  dt = time/n

  r = ode(dt_func).set_integrator('zvode', \
                                  method='bdf')

  x0 = list(map(lambda v: eval(sim.initial_cond(v)), \
                state_vars))
  r.set_initial_value(x0,t=0.0)
  tqdm_segs = 500
  last_seg = 0
  res = ADPSimResult(sim)
  with tqdm.tqdm(total=tqdm_segs) as prog:
    while r.successful() and r.t < time:
        res.add_point(r.t,r.y)
        r.integrate(r.t + dt)
        # update tqdm
        seg = int(tqdm_segs*float(r.t)/float(time))
        if seg != last_seg:
            prog.n = seg
            prog.refresh()
            last_seg = seg

  return res


def plot_adp_simulation(adp,result,plot_file,reference=None):
  fig, axs = plt.subplots(result.num_vars)
  for idx,stvar in enumerate(result.state_vars):
    T,Y = result.data(stvar)
    axs[idx].plot(T,Y)
    axs[idx].set_title(stvar.key)

  print(plot_file)
  plt.savefig(plot_file)
  plt.clf()


def simulate(dev,adp,plot_file):
  print(adp.metadata)
  prog = adp.metadata[adplib.ADPMetadata.Keys.DSNAME]
  dssim = DSProgDB.get_sim(prog)
  sim =  \
         buildsim.build_simulation(dev, \
                                   adp)
  result = run_adp_simulation(dev, \
                             dssim, \
                             sim)
  plot_adp_simulation(adp,result,plot_file)

  raise NotImplementedError
