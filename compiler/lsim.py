import compiler.lsim_pass.buildsim as buildsim
from dslang.dsprog import DSProgDB
import hwlib.adp as adplib
import numpy as np
import matplotlib.pyplot as plt

def run_adp_simulation(dev, \
                       adp, \
                       dssim, \
                       recover=False, \
                       enable_model_error=True, \
                       enable_physical_model=True, \
                       enable_intervals=True, \
                       enable_quantization=True):
  sim =  \
         buildsim.build_simulation(dev, \
                                   adp, \
                                   enable_model_error=enable_model_error, \
                                   enable_physical_model=enable_physical_model, \
                                   enable_intervals=enable_intervals,
                                   enable_quantization=enable_quantization)

  res = buildsim.run_simulation(sim,dssim.sim_time)
  times,values = buildsim.get_dsexpr_trajectories(dev,adp,sim,res, \
                                                  recover=recover)
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
                       enable_model_error=True, \
                       enable_physical_model=True, \
                       enable_intervals=True, \
                       enable_quantization=True):
  print(adp.metadata)
  prog = adp.metadata[adplib.ADPMetadata.Keys.DSNAME]
  dssim = DSProgDB.get_sim(prog)
  dev.model_number = adp.metadata[adplib.ADPMetadata.Keys.RUNTIME_PHYS_DB]
  times,values = run_adp_simulation(dev, \
                                    adp,
                                    dssim, \
                                    enable_model_error=enable_model_error, \
                                    enable_physical_model=enable_physical_model, \
                                    enable_quantization=enable_quantization)
  plot_simulation(times,values,plot_file)




def simulate_reference(dev,prog,plot_file):
  dssim = DSProgDB.get_sim(prog.name)
  T,Z = prog.execute(dssim)
  plot_simulation(T,Z,plot_file)
