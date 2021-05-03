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
import compiler.lwav_pass.vis_util as visutil


def print_summary(dev,adp):
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = DSProgDB.get_info(program.name)
    rmse = adp.metadata.get(ADPMetadata.Keys.LWAV_NRMSE)

    print("------------ metadata ----------------")
    print(adp.metadata)

    runtime = dev.time_constant/adp.tau*dssim.sim_time
    bandwidth = (1.0/dev.time_constant)*adp.tau
    power = energymodel.compute_power(adp,bandwidth)
    energy = runtime*power

    print("--------    general -------------")
    print("runtime = %f ms" % (runtime*1000))
    print("power    = %f mW" % (power*1e3))
    print("energy  = %f uJ" % (energy*1e6))
    print("quality = %f %%" % rmse)
    return []

def print_compensation_comparison(adps):
    series = {
        ("ideal","minimize_error"): "ideal",
        ("phys","minimize_error"): "minerr",
        ("phys","maximize_fit"): "maxfit"
    }
    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    for (lgraph_id,no_scale,one_mode,scale_objective),adp_group in  \
        visutil.adps_groupby(adps,[ADPMetadata.Keys.LGRAPH_ID,  \
                           ADPMetadata.Keys.LSCALE_NO_SCALE, \
                           ADPMetadata.Keys.LSCALE_ONE_MODE, \
                           ADPMetadata.Keys.LSCALE_OBJECTIVE]):

        kwargs = visutil.make_plot_kwargs(lgraph_id=lgraph_id, \
                                  no_scale=no_scale, one_mode=one_mode, \
                                  scale_objective=scale_objective) 

        dataset = {}
        for (scale_method,calib_obj), plot_adps in visutil.adps_groupby(adp_group, \
                                                     [ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                                      ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):

            values = visutil.adps_get_values(plot_adps, ADPMetadata.Keys.LWAV_NRMSE)
            series_name = series[(scale_method,calib_obj)]
            dataset[series_name] = values


        series_order = ["ideal","minerr","maxfit"]
        if any(map(lambda ser: not ser in dataset, series_order)):
            continue

        boxwhisk = boxlib.BoxAndWhiskerVis('compensate', \
                                       xaxis='compensation method',
                                       yaxis='% rmse',
                                       title='%s' % program)

        for ser in series_order:
            boxwhisk.add_data(ser,dataset[ser])

        yield kwargs,boxwhisk

def print_random_comparison(adps):
    adp = adps[0]
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])

    series = {
        'qtytau': 'balanced',
        'rand':'random'
    }
    for (lgraph_id,no_scale,one_mode,scale_method,calib_obj),adp_group in  \
        visutil.adps_groupby(adps,[ADPMetadata.Keys.LGRAPH_ID,  \
                           ADPMetadata.Keys.LSCALE_NO_SCALE, \
                           ADPMetadata.Keys.LSCALE_ONE_MODE, \
                           ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                           ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):

        kwargs = visutil.make_plot_kwargs(lgraph_id=lgraph_id, \
                                  no_scale=no_scale, one_mode=one_mode, \
                                  scale_method=scale_method, \
                                  calib_objective=calib_obj)


        dataset = {}
        for (scale_objective,), plot_adps in visutil.adps_groupby(adp_group, \
                                                     [ADPMetadata.Keys.LSCALE_OBJECTIVE]):
            values = visutil.adps_get_values(plot_adps, ADPMetadata.Keys.LWAV_NRMSE)
            series_name = series[scale_objective]
            dataset[series_name] = values


        series_order = ["balanced","random"]
        if any(map(lambda ser: not ser in dataset, series_order)):
            continue

        boxwhisk = boxlib.BoxAndWhiskerVis('rand', \
                                           xaxis='calibration objective',\
                                           yaxis='% rmse',
                                           title='%s' % program)

        boxwhisk.draw_minimum = True
        boxwhisk.show_outliers = False
        for ser in series_order:
            boxwhisk.add_data(ser,dataset[ser])
        yield kwargs, boxwhisk




def print_aggregate_summaries(dev,adps):
    print("------------ metadata ----------------")
    print(adps[0].metadata)

    vises = []

    for kwargs,vis in print_compensation_comparison(adps):
        vises.append((kwargs,vis))

    for kwargs,vis in print_random_comparison(adps):
        vises.append((kwargs,vis))


    return vises
