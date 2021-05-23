import hwlib.adp as adplib
from hwlib.adp import ADP,ADPMetadata

import compiler.lwav_pass.vis_util as visutil

import compiler.lwav_pass.vis_lscale_stats_util as statsutil
import compiler.lwav_pass.vis_lscale_stats_plots as lscale_plots
import compiler.lwav_pass.vis_lscale_stats_correlations as lscale_corr
import compiler.lwav_pass.vis_lscale_stats_bestadp as lscale_bestadp
import compiler.lwav_pass.vis_lscale_stats_xformsummary as lscale_xform
import compiler.lwav_pass.vis_lscale_stats_signalusage as lscale_signalusage
import compiler.lwav_pass.vis_lscale_stats_equations as lscale_equations
import compiler.lwav_pass.vis_util as vislib

import compiler.lscale_pass.lscale_dynsys as lscaleprob
import compiler.lscale_pass.lscale_ops as lscalelib

import hwlib.block as blocklib
import hwlib.device as devlib

import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
import ops.base_op as baseoplib


from dslang.dsprog import DSProgDB
import numpy as np
import math
import re



def print_aggregate_summaries(dev,args,adps,bounds=None):

    if args.equations:
        lscale_equations.scaled_circuit_block_equation_summary(dev,adps)

    if args.lscale_static:
        lscale_xform.quality_measure_summary(dev,adps)
        lscale_xform.scaling_transform_summary(dev,adps)
        lscale_signalusage.signal_coverage_summary(dev,adps)

    if args.lscale_correlation:
        lscale_corr.signal_correlation_summary(dev,adps)
        lscale_corr.quality_correlation_summary(dev,adps)

    if args.lscale_top5:
        lscale_bestadp.top_circuit_summary(dev,adps)

    vises = []
    if args.lscale_delta_model_plots:
        for kwargs,vis in lscale_plots.print_compensation_comparison(adps):
            vises.append((kwargs,vis))


    if args.lscale_scale_objective_plots:
        for kwargs,vis in lscale_plots.print_random_comparison(adps):
            vises.append((kwargs,vis))


    return vises
