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

def print_aggregate_summaries(dev,adps):
    print("------------ metadata ----------------")
    print(adps[0].metadata)

    rmses = []
    for adp in adps:
        rmse = adp.metadata.get(ADPMetadata.Keys.LWAV_NRMSE)
        rmses.append(rmse)

    boxwhisk = boxlib.BoxAndWhiskerVis('rmses','nrmse','% rmse')
    return [boxwhisk]
