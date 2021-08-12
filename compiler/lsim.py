import compiler.lsim_pass.buildsim as buildsim
from dslang.dsprog import DSProgDB
import hwlib.adp as adplib
import numpy as np
import matplotlib.pyplot as plt

def run_adp_simulation(dev, \
                       adp, \
                       dssim, \
                       recover=False, \
                       unscaled=False, \
                       enable_model_error=True, \
                       enable_physical_model=True, \
                       enable_intervals=True, \
                       enable_quantization=True):
  sim =  \
         buildsim.build_simulation(dev, \
                                   adp, \
                                   unscaled=unscaled,\
                                   enable_model_error=enable_model_error, \
                                   enable_physical_model=enable_physical_model, \
                                   enable_intervals=enable_intervals, \
                                   enable_quantization=enable_quantization)

  res = buildsim.run_simulation(sim,dssim.sim_time)
  times,values = buildsim.get_dsexpr_trajectories(dev,adp,sim,res, \
                                                  recover=recover)
  return times,values


def get_style():
  linestyle= {
    'linewidth':4.0
  }
  fontstyle = {
    "size": 22
  }
  axestyle = {
    'linewidth':2.0
  }
  return linestyle,fontstyle,axestyle

def plot_separate_simulations(times,stvars,plot_file):
  linestyle,fontstyle,axestyle = get_style()
  ordered_entries = list(stvars.keys())
  ordered_entries.sort()
  assert("{variable}" in plot_file)

  plt.rc('font',**fontstyle)
  plt.rc('axes',**axestyle)
  for idx,stvar in enumerate(ordered_entries):
      final_plot_file = plot_file.format(variable=stvar)
      values = stvars[stvar]
      fig,ax = plt.subplots()
      fig.patch.set_visible(False)
      ax.spines["right"].set_visible(False)
      ax.spines["top"].set_visible(False)
      ax.plot(times,values,**linestyle)
      ax.set_title("%s" % stvar)
      ax.set_xlabel("Time (simulation units)")
      ax.set_ylabel("Amplitude")
      fig.tight_layout()
      fig.savefig(final_plot_file)
      plt.clf()


def plot_simulation(times,stvars,plot_file):
  linestyle,fontstyle,axestyle = get_style()
  ordered_entries = list(stvars.keys())
  ordered_entries.sort()
  assert(not "variable" in plot_file)

  plt.rc('font',**fontstyle)
  plt.rc('axes',**axestyle)
  fig, axs = plt.subplots(len(stvars.keys()),figsize=(15,15))
  for idx,stvar in enumerate(ordered_entries):
    values = stvars[stvar]
    axs[idx].spines["right"].set_visible(False)
    axs[idx].spines["top"].set_visible(False)
    axs[idx].plot(times,values,**linestyle)
    axs[idx].set_title("%s" % stvar)


  plt.tight_layout()
  plt.savefig(plot_file)
  plt.clf()


def simulate_adp(dev,adp,plot_file, \
                 unscaled=False,\
                 enable_model_error=True, \
                 enable_physical_model=True, \
                 enable_intervals=True, \
                 enable_quantization=True, \
                 separate_figures=False):
  print(adp.metadata)
  prog = adp.metadata[adplib.ADPMetadata.Keys.DSNAME]
  dssim = DSProgDB.get_sim(prog)
  if not unscaled:
      dev.model_number = adp.metadata[adplib.ADPMetadata.Keys.RUNTIME_PHYS_DB] if \
              adp.metadata.has(adplib.ADPMetadata.Keys.RUNTIME_PHYS_DB) else None

  times,values = run_adp_simulation(dev, \
                                    adp,
                                    dssim, \
                                    unscaled=unscaled,  \
                                    enable_intervals=enable_intervals,\
                                    enable_model_error=enable_model_error, \
                                    enable_physical_model=enable_physical_model, \
                                    enable_quantization=enable_quantization)
  if separate_figures:
    plot_separate_simulations(times,values,plot_file)
  else:
    plot_simulation(times,values,plot_file)





def simulate_reference(dev,prog,plot_file,separate_figures=False):
  dssim = DSProgDB.get_sim(prog.name)
  T,Z = prog.execute(dssim)
  if separate_figures:
    plot_separate_simulations(T,Z,plot_file)
  else:
    plot_simulation(T,Z,plot_file)
