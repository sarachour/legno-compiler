#from compiler import lgraph, lscale, srcgen, execprog
import os
import time
import json
import shutil
import signal
import numpy as np

import util.util as util
import util.paths as paths

from hwlib.adp import ADP,ADPMetadata
import hwlib.hcdc.llenums as llenums
import runtime.runtime_meta_util as runt_meta_util
import json

def get_unscaled_adp(dev,adp):
        path_handler = paths.PathHandler( \
                                      adp.metadata.get(ADPMetadata.Keys.FEATURE_SUBSET), \
                                     adp.metadata.get(ADPMetadata.Keys.DSNAME))
        filename = path_handler.lgraph_adp_file(adp.metadata.get(ADPMetadata.Keys.LGRAPH_ID))

        with open(filename,'r') as fh:
                unsc_adp_obj = json.loads(fh.read())
                unsc_adp = ADP.from_json(dev, unsc_adp_obj)
                return unsc_adp

        raise Exception("could not find unscaled ADP")

def get_statistics(times):
        med = np.median(times)
        q3 = np.percentile(times,75)
        q1 = np.percentile(times,25)
        min_val = min(times)
        max_val = max(times)
        return med,q3-q1,min_val,max_val


def adps_groupby(adps,fields):
    groups = {}
    for adp in adps:
        key = tuple(list(map(lambda f: adp.metadata.get(f),fields)))
        if not key in groups:
            groups[key] = []

        groups[key].append(adp)

    for key,adp_group in groups.items():
        yield key,adp_group

def has_waveforms(adps):
    return all(map(lambda adp: adp.metadata.has(ADPMetadata.Keys.LWAV_NRMSE), adps))

def adps_get_values(adps,field):
    return list(map(lambda adp: adp.metadata[field], adps))

def make_plot_kwargs(lgraph_id=None, lscale_id=None, one_mode=None, no_scale=None, \
                     scale_objective=None, scale_method=None,calib_objective=None):
    kwargs = {}
    if not lgraph_id is None:
        kwargs['graph_index'] = lgraph_id

    if not lscale_id is None:
        kwargs['scale_index'] = lscale_id

    if not one_mode is None:
        kwargs['one_mode'] = one_mode

    if not no_scale is None:
        kwargs['no_scale'] = no_scale

    if not scale_objective is None:
        kwargs['opt'] = scale_objective

    if not scale_method is None:
        kwargs['model'] = scale_method

    if not calib_objective is None:
        kwargs['calib_obj'] = llenums.CalibrateObjective(calib_objective)

    return kwargs
