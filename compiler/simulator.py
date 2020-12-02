import numpy as np
import tqdm
import os
import matplotlib.pyplot as plt
import json
from util import paths

from scipy.integrate import ode

import compiler.sim_pass.build_sim as buildsim
from dslang.dsprog import DSProgDB
from hwlib.adp import AnalogDeviceProg

def evaluate(expr,var_dict={}):
  var_dict['np'] = np
  return eval(expr,var_dict)

def next_state(derivs,variables,values):
  vdict = dict(zip(map(lambda v: "%s_" % v, \
                       variables),values))
  next_vdict = {}
  for v in variables:
    next_vdict[v] = evaluate(derivs[v],vdict)
  result = list(map(lambda v: next_vdict[v], \
                    variables))
  return result


def plot_adp_simulation(path_handler,dssim,adp_path,V,T,Y):
  fileargs = \
             path_handler.lscale_adp_to_args(adp_path)

  Z =dict(map(lambda v: (v,[]), V))
  for t,y in zip(T,Y):
    for var,value in zip(V,y):
      Z[var].append(value)

  for series_name,values in Z.items():
      print("%s: %d" % (series_name,len(values)))

  for series_name,values in Z.items():
    filepath = path_handler.adp_sim_plot(fileargs['lgraph'], \
                                         fileargs['lscale'], \
                                         fileargs['opt'], \
                                         fileargs['model'], \
                                         series_name)
    print('plotting %s' % series_name)
    plt.plot(T,values,label=series_name)
    plt.savefig(filepath)
    plt.clf()

def run_adp_simulation(board, \
                       adp, \
                       init_conds, \
                       derivs, \
                       dssim):
  var_order = list(init_conds.keys())

  def dt_func(t,vs):
    return next_state(derivs,var_order,vs)

  time = dssim.sim_time/(adp.tau)
  n = 300.0
  dt = time/n

  r = ode(dt_func).set_integrator('zvode', \
                                  method='bdf')

  x0 = list(map(lambda v: eval(init_conds[v]), \
                var_order))
  r.set_initial_value(x0,t=0.0)
  tqdm_segs = 500
  last_seg = 0
  T = []
  Y = []
  with tqdm.tqdm(total=tqdm_segs) as prog:
    while r.successful() and r.t < time:
        T.append(r.t/adp.board.time_constant)
        Y.append(r.y)
        r.integrate(r.t + dt)
        seg = int(tqdm_segs*float(r.t)/float(time))
        if seg != last_seg:
            prog.n = seg
            prog.refresh()
            last_seg = seg

  return var_order,T,Y

def plot_reference_simulation(path_handler,prob,dssim):
    T,Z = prob.execute(dssim)
    for series_name,values in Z.items():
        print("%s: %d" % (series_name,len(values)))

    plt.rcParams.update({'font.size': 22})
    for series_name,values in Z.items():
      plot_file = path_handler.ref_sim_plot(series_name)
      print('plotting %s' % series_name)
      plt.plot(T,values,label=series_name,linewidth=4)
      plt.savefig(plot_file)
      plt.clf()


def simulate(args):
  import hwlib.hcdc.hwenvs as hwenvs
  from hwlib.hcdc.hcdcv2_4 import make_board
  from hwlib.hcdc.globals import HCDCSubset
  dssim = DSProgDB.get_sim(args.program)
  path_handler = paths.PathHandler(args.subset,args.program)

  
  if args.reference:
    ref_prog = DSProgDB.get_prog(args.program)
    if args.runtime:
      result = ref_prog.execute_and_profile(dssim)
      print("runtime: %e seconds" % result)
    else:
      plot_reference_simulation(path_handler, ref_prog,dssim)

  if args.adp:
    board = make_board(HCDCSubset(args.subset), \
                              load_conns=False)
    adp = AnalogDeviceProg.read(board, args.adp)
    init_conds,derivs =  \
                        buildsim.build_simulation(board, \
                                                  adp,
                                                  args.mode)
    V,T,Y = run_adp_simulation(board, \
                               adp, \
                               init_conds, \
                               derivs, \
                               dssim)
    plot_adp_simulation(path_handler,dssim,args.adp,V,T,Y)
