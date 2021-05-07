#from compiler import lgraph, lscale, srcgen, execprog
import os
import time
import json
import shutil
import signal
import numpy as np
import itertools

import util.util as util
import util.paths as paths
from dslang.dsprog import DSProgDB

from hwlib.adp import ADP,ADPMetadata
import hwlib.adp_renderer as adprender
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.energy_model as energymodel

import runtime.runtime_meta_util as runt_meta_util

import compiler.lwav_pass.boxandwhisker as boxlib
import compiler.lwav_pass.scatter as  scatterlib
import compiler.lwav_pass.vis_util as visutil
import compiler.lwav_pass.table as tbllib

def compute_power_quality_runtime(dev,adps):
    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = DSProgDB.get_info(program.name)
    rmses = visutil.adps_get_values(adps,ADPMetadata.Keys.LWAV_NRMSE)
    runtimes = list(map(lambda adp: dev.time_constant/adp.tau*dssim.sim_time, adps))
    bandwidths = list(map(lambda adp: 1.0/dev.time_constant*adp.tau, adps))
    powers = list(map(lambda tup: energymodel.compute_power(tup[0],tup[1]), \
                        zip(adps, bandwidths)))
    energies = list(map(lambda tup: tup[0]*tup[1], \
                        zip(runtimes, powers)))

    return np.array(rmses),np.array(runtimes),np.array(powers),np.array(energies)

def print_performance_summary(dev,adps):
    def fancy_name(adp):
        names = {
            ("minimize_error","ideal"): "ideal",
            ("maximize_fit","phys"):"maxfit",
            ("minimize_error","phys"):"minerr"
        }
        fmt = "{calib_obj}/{scale_method}"
        key = (adp.metadata.get(ADPMetadata.Keys.RUNTIME_CALIB_OBJ), \
        adp.metadata.get(ADPMetadata.Keys.LSCALE_SCALE_METHOD))
        name = names[key]

        objective = adp.metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE) 
        if objective != "qtytau":
            name += "/" + objective
        if adp.metadata.get(ADPMetadata.Keys.LSCALE_ONE_MODE):
            name += " (one mode)"
        if adp.metadata.get(ADPMetadata.Keys.LSCALE_NO_SCALE):
            name += "(no scale)"

        return name

    def get_joint_minimum(primary,secondary):
        tol = 1e-6
        idx = np.argmin(primary)
        subinds = list(filter(lambda i: abs(primary[i] - primary[idx] ) < tol , \
                           range(len(primary))))
        best_idx = min(subinds, key=lambda i: secondary[i])
        return best_idx

    if not visutil.has_waveforms(adps):
        return

    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = DSProgDB.get_info(program.name)

    pr_vis = scatterlib.ScatterVis("powerVruntime",
                          title="% power v.s. runtime",
                          xlabel="runtime (ms)", \
                          ylabel="power (mW)")
    pr_vis.show_legend = True

    qr_vis = scatterlib.ScatterVis("rmseVruntime",
                          title="% rmse v.s. runtime",
                          xlabel="runtime (ms)", \
                          ylabel="% rmse")
    qr_vis.show_legend = True

    qe_vis = scatterlib.ScatterVis("rmseVenergy",
                          title="% rmse v.s. runtime",
                          xlabel="energy (uJ)", \
                          ylabel="% rmse")
    qr_vis.show_legend = True


    valid_scale_methods = ['phys']
    valid_scale_objectives = ['qtytau']


    energy_scale = 1e6
    power_scale= 1e3
    runtime_scale = 1e3

    legend = {'minimize_error':'minerr','maximize_fit':'maxfit'}
    valid_adps = []
    for (no_scale,one_mode,scale_method,scale_objective,calib_obj),adp_group in  \
        visutil.adps_groupby(adps,[ADPMetadata.Keys.LSCALE_NO_SCALE, \
                                   ADPMetadata.Keys.LSCALE_ONE_MODE, \
                                   ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                   ADPMetadata.Keys.LSCALE_OBJECTIVE, \
                                   ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):
        if one_mode or no_scale:
            continue


        if not scale_method in valid_scale_methods or \
           not scale_objective in valid_scale_objectives:
            continue

        valid_adps += list(adp_group)

        rmses,runtimes,powers,energies = compute_power_quality_runtime(dev,adp_group)
        pr_vis.add_series(legend[calib_obj], runtimes*runtime_scale, powers*power_scale)
        qr_vis.add_series( legend[calib_obj], runtimes*runtime_scale, rmses)
        qe_vis.add_series( legend[calib_obj], energies*energy_scale, rmses)


    kwargs = visutil.make_plot_kwargs()
    yield kwargs,pr_vis
    yield kwargs,qr_vis
    yield kwargs,qe_vis

    rmses,runtimes,powers,energies = compute_power_quality_runtime(dev,valid_adps)
    tbl = tbllib.Tabular(["benchmark","criteria","\\%rmse","runtime (ms)","power (mW)","energy (uJ)","best adp","circuit \\#"], \
                         ["%s","%s","%.3e","%.2f","%.2f", "%.2f", "%s", "%d"])

    idx = np.argmin(rmses)
    circuit_number = adps[idx].metadata.get(ADPMetadata.Keys.LGRAPH_ID)
    tbl.add([dsinfo.name, "\\% rmse", rmses[idx], runtimes[idx]*runtime_scale,  \
             powers[idx]*power_scale, energies[idx]*energy_scale,  fancy_name(valid_adps[idx]),circuit_number], \
            emph=[False,False,True,False,False,False,False,False])

    idx = np.argmin(runtimes)
    idx = get_joint_minimum(runtimes,rmses)
    circuit_number = adps[idx].metadata.get(ADPMetadata.Keys.LGRAPH_ID)
    tbl.add([dsinfo.name, "runtime", rmses[idx], runtimes[idx]*runtime_scale,  \
             powers[idx]*power_scale, energies[idx]*energy_scale,  fancy_name(valid_adps[idx]),circuit_number], \
            emph=[False,False,False,True,False,False,False,False])


    idx = get_joint_minimum(powers,rmses)
    circuit_number = adps[idx].metadata.get(ADPMetadata.Keys.LGRAPH_ID)
    tbl.add([dsinfo.name, "power", rmses[idx], runtimes[idx]*runtime_scale,  \
             powers[idx]*power_scale, energies[idx]*energy_scale,  fancy_name(valid_adps[idx]),circuit_number], \
            emph=[False,False,False,False,True,False,False,False])


    idx = get_joint_minimum(energies,rmses)
    circuit_number = adps[idx].metadata.get(ADPMetadata.Keys.LGRAPH_ID)
    tbl.add([dsinfo.name, "energy", rmses[idx], runtimes[idx]*runtime_scale,  \
             powers[idx]*power_scale, energies[idx]*energy_scale,  fancy_name(valid_adps[idx]),circuit_number], \
            emph=[False,False,False,False,False,True,False,False])



    print("----- power, energy, quality, runtime -----")
    print(tbl.render())
    print("\n")
    idx = np.argmin(rmses)



def print_compile_time_summary(dev,adps):
    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(program.name)

    for (no_scale,one_mode),adp_group in  \
        visutil.adps_groupby(adps,[ADPMetadata.Keys.LSCALE_NO_SCALE, \
                                   ADPMetadata.Keys.LSCALE_ONE_MODE]):

        header = ["benchmark","median","iqr","min","max","median","iqr","min","max"]

        tbl = tbllib.Tabular(header, \
                             ["%s"]+["%.2f"]*(len(header)-1))


        lgraph_times = visutil.adps_get_values(adps,ADPMetadata.Keys.LGRAPH_RUNTIME)
        lg_med, lg_iqr, lg_min,lg_max = visutil.get_statistics(lgraph_times)
        lscale_times = visutil.adps_get_values(adps,ADPMetadata.Keys.LSCALE_RUNTIME)
        ls_med, ls_iqr, ls_min,ls_max = visutil.get_statistics(lscale_times)
        tbl.add([dsinfo.name,lg_med,lg_iqr,lg_min,lg_max,ls_med,ls_iqr,ls_min,ls_max])

        flags = ""
        if no_scale:
            flags += "(no scale)"
        if one_mode:
            flags += "(one mode)"

        print("------ runtime statistics %s -----" % flags)
        print(tbl.render())
        print("\n")

    return []

def print_aggregate_summaries(dev,adps):
    print("------------ metadata ----------------")
    print(adps[0].metadata)

    vises = []
    for vis in print_performance_summary(dev,adps):
        yield vis

    for vis in print_compile_time_summary(dev,adps):
        yield vis

        yield vis

    return vises
