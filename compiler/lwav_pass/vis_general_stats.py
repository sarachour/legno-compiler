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
        objectives = {
            'rand': 'single'
        }
        fmt = "{calib_obj}/{scale_method}"
        key = (adp.metadata.get(ADPMetadata.Keys.RUNTIME_CALIB_OBJ), \
        adp.metadata.get(ADPMetadata.Keys.LSCALE_SCALE_METHOD))
        name = names[key]

        objective = adp.metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE) 
        if objective != "qtytau":
            name = objectives[objective]
        if adp.metadata.get(ADPMetadata.Keys.LSCALE_ONE_MODE):
            name += " (one mode)"
        if adp.metadata.get(ADPMetadata.Keys.LSCALE_NO_SCALE):
            name += "(no scale)"

        return name

    def get_joint_minimum(primary,secondary):
        tol = 1e-10
        min_value = min(primary)
        subinds = list(filter(lambda i: abs(primary[i] - min_value ) < tol , \
                           range(len(primary))))
        best_idx = min(subinds, key=lambda i: secondary[i])
        print(min_value,secondary[best_idx])
        return best_idx

    if not visutil.has_waveforms(adps):
        return

    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = DSProgDB.get_info(program.name)



    energy_scale = 1e6
    power_scale= 1e3
    runtime_scale = 1e3

    for (circuit_number,no_scale,one_mode),adps_supergroup in  \
        visutil.adps_groupby(adps,[ \
                                    ADPMetadata.Keys.LGRAPH_ID, \
                                    ADPMetadata.Keys.LSCALE_NO_SCALE, \
                                    ADPMetadata.Keys.LSCALE_ONE_MODE]):

        tag = "(nomaster)" if one_mode else ""
        tag += "(noscale)" if no_scale else ""

        qr_vis = scatterlib.ScatterVis("rmseVruntime",
                            title="% rmse v.s. runtime",
                            xlabel="log(% rmse)", \
                            ylabel="log(runtime)")
        #qr_vis.show_legend = True
        qr_vis.x_logscale = True
        qr_vis.y_logscale = True

        qp_vis = scatterlib.ScatterVis("rmseVpower", \
                                       title="% rmse v.s. power", \
                                       xlabel="log(% rmse)", \
                                       ylabel="log(power)")
        #qp_vis.show_legend = True
        qp_vis.x_logscale = True
        qp_vis.y_logscale = True

        qe_vis = scatterlib.ScatterVis("rmseVenergy",
                            title="% rmse v.s. energy",
                                       xlabel="log(% rmse)", \
                                       ylabel="log(energy)")
        #qe_vis.show_legend = True
        qe_vis.x_logscale = True
        qe_vis.y_logscale = True

        if one_mode or no_scale:
                valid_scale_methods = ['ideal']
        else:
                valid_scale_methods = ['phys']

        valid_scale_objectives = ['qtytau','rand']
        legend = { \
                   ('minimize_error','qtytau'):'min', \
                   ('minimize_error','rand'):'sng/min', \
                   ('maximize_fit','qtytau'):'max', 
                   ('maximize_fit','rand'):'sng/max', \
        }
        dark = "#303952"
        light="#e84118"
        dark2 = "#192a56"
        light2="#c23616"

        styles = {
            "min": (dark,"x",100),
            "sng/min":(light,"x",100),
            "max": (dark2,"^",80),
            "sng/max": (light2, "^",80)

        }
        order = ["sng/min","sng/max","min","max"]
        valid_adps = []
        series = []
        for (scale_method,scale_objective,calib_obj),adp_group in  \
            visutil.adps_groupby(adps_supergroup,[ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                    ADPMetadata.Keys.LSCALE_OBJECTIVE, \
                                    ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):

            if not scale_method in valid_scale_methods or \
            not scale_objective in valid_scale_objectives:
                continue

            valid_adps += list(adp_group)

            rmses,runtimes,powers,energies = compute_power_quality_runtime(dev,adp_group)
            name = legend[(calib_obj,scale_objective)]
            series.append(name)
            qr_vis.add_series(name, rmses,runtimes*runtime_scale)
            qr_vis.set_style(name,styles[name][0],styles[name][1],size=styles[name][2])
            qp_vis.add_series(name, rmses, powers*power_scale)
            qp_vis.set_style(name,styles[name][0],styles[name][1],size=styles[name][2])
            qe_vis.add_series(name, rmses,energies*energy_scale)
            qe_vis.set_style(name,styles[name][0],styles[name][1],size=styles[name][2])


        qp_vis.order = order
        qr_vis.order = order
        qe_vis.order = order
        if len(valid_adps) == 0:
            continue

        if not len(series) == 4:
            continue

        kwargs = visutil.make_plot_kwargs()
        if not no_scale and not one_mode:
            yield kwargs,qr_vis
            yield kwargs,qp_vis
            yield kwargs,qe_vis

        rmses,runtimes,powers,energies = compute_power_quality_runtime(dev,valid_adps)
        tbl = tbllib.Tabular(["benchmark","criteria","\\%rmse","runtime (ms)","power (mW)","energy (uJ)","best adp"], \
                            ["%s","%s","%.3e","%.2f","%.2f", "%.2f", "%s"])

        idx = np.argmin(rmses)
        tbl.add([dsinfo.name, "\\% rmse", rmses[idx], runtimes[idx]*runtime_scale,  \
                powers[idx]*power_scale, energies[idx]*energy_scale,  fancy_name(valid_adps[idx])], \
                emph=[False,False,True,False,False,False,False])

        idx = np.argmin(runtimes)
        idx = get_joint_minimum(runtimes,rmses)
        tbl.add([dsinfo.name, "runtime", rmses[idx], runtimes[idx]*runtime_scale,  \
                powers[idx]*power_scale, energies[idx]*energy_scale,  fancy_name(valid_adps[idx])], \
                emph=[False,False,False,True,False,False,False])


        idx = get_joint_minimum(powers,rmses)
        tbl.add([dsinfo.name, "power", rmses[idx], runtimes[idx]*runtime_scale,  \
                powers[idx]*power_scale, energies[idx]*energy_scale,  fancy_name(valid_adps[idx])], \
                emph=[False,False,False,False,True,False,False])


        idx = get_joint_minimum(energies,rmses)
        tbl.add([dsinfo.name, "energy",  \
                 rmses[idx], runtimes[idx]*runtime_scale,  \
                powers[idx]*power_scale, energies[idx]*energy_scale,  fancy_name(valid_adps[idx])], \
                emph=[False,False,False,False,False,True,False])



        print("----- power, energy, quality, runtime %s (circuit=%d)-----" % (tag,circuit_number))
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

def print_aggregate_summaries(dev,args,adps):
    vises = []
    if args.performance:
        for vis in print_performance_summary(dev,adps):
            vises.append(vis)

    if args.compile_times:
        print_compile_time_summary(dev,adps)

    return vises
