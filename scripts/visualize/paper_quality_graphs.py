
from scripts.common import ExecutionStatus
from scripts.expdriver_db import ExpDriverDB
import scripts.analysis.quality as quality_analysis

import dslang.dsprog as dsproglib
from dslang.dsprog import DSProgDB
import util.util as util
import scripts.visualize.common as common
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import math
'''
YLABELS = {
  'micro-osc': 'amplitude',
  'micro-osc-with-gain': 'amplitude',
  'vanderpol': 'amplitude',
  'pend': 'position',
  'closed-forced-vanderpol': 'amplitude',
  'robot': 'xvel',
  'pend-nl': 'position',
  'lotka': 'population',
  'spring': 'position',
  'cosc': 'amplitude',
  'kalman-const': 'constant',
  'spring-nl': 'position',
  'heat1d-g2': 'heat',
  'heat1d-g4': 'heat',
  'heat1d-g4-wg': 'heat',
  'heat1d-g8': 'heat',
  'heat1d-g9': 'heat',
  'heat1d-g8-wg': 'heat',
  'gentoggle':'conc',
  'bont':'conc',
  'smmrxn':'conc',
  'epor':'conc',
  'kalman-const':'state',
  'kalman-freq-small':'state'
}
'''

def plot_preamble_realtime(entry):
  # compute reference using information from first element
  output = list(entry.outputs())[0]
  palette = sns.color_palette()
  ax = plt.subplot(1, 1, 1)
  info = DSProgDB.get_info(entry.program)
  title = info.name
  ax.set_xlabel('time (ms)',fontsize=18)
  ax.tick_params(labelsize=16);
  ax.set_ylabel(info.units,fontsize=18)
  #ax.set_xticklabels([])
  #ax.set_yticklabels([])
  #ax.set_title(title,fontsize=20)
  ax.grid(False)
  return ax

def plot_preamble(entry,TREF,YREF):
 # compute reference using information from first element
  output = list(entry.outputs())[0]
  palette = sns.color_palette()
  ax = plt.subplot(1, 1, 1)
  info = DSProgDB.get_info(entry.program)
  title = info.name
  ax.set_xlabel('simulation time',fontsize=18)
  ax.set_ylabel(info.units,fontsize=18)
  ax.set_xticklabels([])
  ax.set_yticklabels([])
  #ax.set_title(title,fontsize=20)
  ax.set_xlim((min(TREF),max(TREF)))
  margin = (max(YREF)-min(YREF))*0.1
  lb= min(YREF)-margin
  ub = max(YREF)+margin
  ax.set_ylim((lb,ub))
  ax.grid(False)

  ax.plot(TREF,YREF,label='reference',
          linestyle='-', \
          linewidth=3, \
          color='#EE5A24')
  return ax

def plot_waveform(ax,identifier,out,alpha,real_time=False):
    TMEAS,YMEAS = quality_analysis.read_meas_data(out.waveform)
    print(out.transform)
    TREC,YREC = quality_analysis.scale_obs_data(out, \
                                                TMEAS,YMEAS, \
                                                scale_time=not real_time)
    print(min(TREC),max(TREC))
    ax.plot(TREC if not real_time else TREC*1000.0 \
            ,YREC,alpha=alpha,
            label='measured', \
            color='#5758BB', \
            linewidth=3.0, \
            linestyle="-" if real_time else '-' \
    )

    if 'standard' in identifier or real_time:
      clb,cub = ax.get_ylim()
      margin = (max(YREC)-min(YREC))*0.1
      lb= min(YREC)-margin
      ub = max(YREC)+margin
      ax.set_ylim(min(lb,clb),max(ub,cub))

def plot_best(identifier,entry,outputs,filepath,real_time=False):
  output = list(entry.outputs())[0]
  TREF,YREF = quality_analysis.compute_ref(entry.program, \
                                           entry.dssim, \
                                           output.variable)
  if real_time:
    ax = plot_preamble_realtime(entry)
  else:
    ax = plot_preamble(entry,TREF,YREF)

  if real_time:
    best_output = outputs[0]
  else:
    best_output = min( \
                       outputs, \
                       key=lambda o: o.quality)
  plot_waveform(ax,identifier,best_output,1.0,real_time)

  plt.tight_layout()
  plt.savefig(filepath)
  plt.clf()

def plot_reference(identifier,entry,outputs,filepath,real_time=False):
  output = list(entry.outputs())[0]
  TREF,YREF = quality_analysis.compute_ref(entry.program, \
                                           entry.dssim, \
                                           output.variable)
  if real_time:
    ax = plot_preamble_realtime(entry)
  else:
    ax = plot_preamble(entry,TREF,YREF)

  plt.tight_layout()
  plt.savefig(filepath)
  plt.clf()



def plot_average(identifier,entry,outputs,filepath,real_time=False):
  output = list(entry.outputs())[0]
  TREF,YREF = quality_analysis.compute_ref(entry.program, \
                                           entry.dssim, \
                                           output.variable)

  if real_time:
    ax = plot_preamble_realtime(entry)
  else:
    ax = plot_preamble(entry,TREF,YREF)
  weight = math.sqrt(1.0/len(outputs))
  for output in outputs:
    plot_waveform(ax,identifier,output,weight,real_time)

  plt.tight_layout()
  plt.savefig(filepath)
  plt.clf()

def plot_quality(identifier,experiments,real_time=False):
  print(identifier)
  # compute reference using information from first element
  entry = experiments[0]
  #ax = plot_preamble(entry,TREF,YREF)

  qualities = list(map(lambda e: e.quality, experiments))

  outputs = []
  for exp in experiments:
    for out in exp.outputs():
      outputs.append(out)

  valid_outputs = list(filter(lambda o: not o.quality is None or \
                              real_time, outputs))

  if len(valid_outputs) == 0:
    plt.clf()
    return
  filename = "paper-%s-ref.pdf" % (identifier)
  filepath = common.get_path(filename)
  plot_reference(identifier,entry,valid_outputs,filepath,real_time=real_time)
  filename = "paper-%s-best.pdf" % (identifier)
  filepath = common.get_path(filename)
  plot_best(identifier,entry,valid_outputs,filepath,real_time=real_time)
  filename = "paper-%s-average.pdf" % (identifier)
  filepath = common.get_path(filename)
  plot_average(identifier,entry,valid_outputs,filepath,real_time=real_time)

def to_identifier(exp):
  args = util.unpack_model(exp.model)
  key = "%s-%s-%s" % (exp.program,exp.subset,args['model'].value)
  return key.replace('_','-')

def visualize(db):
  by_bmark = {}
  for exp in db.experiment_tbl \
               .get_by_status(ExecutionStatus.RAN):

    dssim = dsproglib.DSProgDB.get_sim(exp.program)
    if exp.quality is None  \
       and not dssim.real_time:
      continue


    key = to_identifier(exp)
    if not key in by_bmark:
      by_bmark[key] = []


    by_bmark[key].append(exp)

  for identifier,experiments in by_bmark.items():
    dssim = dsproglib.DSProgDB.get_sim(experiments[0].program)
    plot_quality(identifier,experiments, \
                 real_time=dssim.real_time)
