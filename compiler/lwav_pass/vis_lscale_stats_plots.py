import hwlib.adp as adplib
from hwlib.adp import ADP,ADPMetadata

import compiler.lwav_pass.waveform as wavelib
import compiler.lwav_pass.histogram as histlib
import compiler.lwav_pass.heatgrid as heatlib
import compiler.lwav_pass.vis_util as visutil
import compiler.lwav_pass.table as tbllib
import compiler.lwav_pass.boxandwhisker as boxlib

import compiler.lwav_pass.vis_lscale_stats_util as statsutil

import compiler.lscale_pass.lscale_dynsys as lscaleprob
import compiler.lscale_pass.lscale_ops as lscalelib

import hwlib.block as blocklib
import hwlib.device as devlib

from dslang.dsprog import DSProgDB
import numpy as np
import math
import re



def print_compensation_comparison(adps):
    series = {
        ("ideal","minimize_error"): "ideal",
        ("phys","minimize_error"): "minerr",
        ("phys","maximize_fit"): "maxfit"
    }
    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(program.name)


    if not visutil.has_waveforms(adps):
        return


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
                                           title='%s' % dsinfo.name)
        boxwhisk.show_outliers = False
        for ser in series_order:
            boxwhisk.add_data(ser,dataset[ser])

        yield kwargs,boxwhisk

def print_random_comparison(adps):
    adp = adps[0]
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])

    series = {
        'qtytau': 'balanced',
        'qty': 'quality',
        'rand':'random'
    }


    if not visutil.has_waveforms(adps):
        return


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


