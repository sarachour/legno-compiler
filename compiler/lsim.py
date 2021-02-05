import compiler.lsim_pass.buildsim as buildsim
from dslang.dsprog import DSProgDB
import hwlib.adp as adplib
import numpy as np
import matplotlib.pyplot as plt

def run_adp_simulation(dev, \
                       adp, \
                       dssim):
  sim =  \
         buildsim.build_simulation(dev, \
                                   adp)
  res = buildsim.run_simulation(sim,dssim.sim_time)
  times,values = buildsim.get_dsexpr_trajectories(dev,adp,sim,res)
  return times,values


def plot_simulation(times,stvars,plot_file):
  fig, axs = plt.subplots(len(stvars.keys()),figsize=(15,15))
  ordered_entries = list(stvars.keys())
  ordered_entries.sort()

  for idx,stvar in enumerate(ordered_entries):
    values = stvars[stvar]
    axs[idx].plot(times,values)
    axs[idx].set_title(stvar)

  print(plot_file)
  plt.tight_layout()
  plt.savefig(plot_file)
  plt.clf()


def simulate_adp(dev,adp,plot_file, \
                 disable_quantize=False, \
                 disable_operating_range=False, \
                 disable_physical_db=False):
  print(adp.metadata)
  prog = adp.metadata[adplib.ADPMetadata.Keys.DSNAME]
  dssim = DSProgDB.get_sim(prog)
  dev.model_number = adp.metadata[adplib.ADPMetadata.Keys.RUNTIME_PHYS_DB]
  times,values = run_adp_simulation(dev, \
                              adp,
                              dssim)
  plot_simulation(times,values,plot_file)




def simulate_reference(dev,prog,plot_file):
  dssim = DSProgDB.get_sim(prog.name)
  T,Z = prog.execute(dssim)
  plot_simulation(T,Z,plot_file)
