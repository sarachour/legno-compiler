import hwlib.adp as adplib
from hwlib.adp import ADP,ADPMetadata

import compiler.lwav_pass.waveform as wavelib
import compiler.lwav_pass.histogram as histlib
import compiler.lwav_pass.heatgrid as heatlib
import compiler.lwav_pass.scatter as scatlib
import compiler.lsim as lsimlib

import compiler.lwav_pass.histogram as histlib

from dslang.dsprog import DSProgDB
import numpy as np
import math


def print_summary(dev,adp):
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = DSProgDB.get_info(program.name)
    rmse = adp.metadata.get(ADPMetadata.Keys.LWAV_NRMSE)

    print("------------ lgraph ----------------")
    by_block = {'fanout':[],'adc':[],'dac':[],'mult':[], 'integ':[], \
                'extout':[],'extin':[],'cin':[],'cout':[],'tin':[],'tout':[]}

    total_blocks = 0
    for cfg in adp.configs:
        if cfg.inst.block in by_block:
            by_block[cfg.inst.block].append(cfg.mode)
        total_blocks +=1

    total_conns = len(list(adp.conns))

    for block_name,modes in by_block.items():
        if len(modes) > 0:
            print("%s = %d modes=%s" % (block_name,len(modes), set(modes)))

    print("total blocks = %d" % total_blocks)
    print("total conns = %d" % total_conns)
    return []

def circuit_quality_analysis_summary(dev,adps):
    get_key = lambda adp: (adp.metadata[ADPMetadata.Keys.LGRAPH_ID])

    rmses = {}
    for adp in adps:
        key = get_key(adp)
        if not key in rmses:
            rmses[key] = []

        rmse = adp.metadata[ADPMetadata.Keys.LWAV_NRMSE]
        rmses[key].append(rmse)

    max_rmse = max(map(lambda vs: max(vs), rmses.values()))
    min_rmse = min(map(lambda vs:  min(vs), rmses.values()))
    vis = heatlib.NormalizedHeatGrid("rmse4graph", "Distribution of % rmse by unscaled adp", \
                                     "% rmse",  10, \
                                     bounds=(min_rmse,max_rmse))

    for circuit_id,rmses in rmses.items():
        norm_rmses = list(map(lambda val: (val-min_rmse)/(max_rmse-min_rmse), rmses))
        vis.add_row(norm_rmses)

    yield vis

def print_aggregate_summaries(dev,adps):
    vises = []
    for vis in circuit_quality_analysis_summary(dev,adps):
        vises.append(vis)

    return vises
