import hwlib.adp as adplib
from hwlib.adp import ADP,ADPMetadata

import compiler.lwav_pass.waveform as wavelib
import compiler.lwav_pass.histogram as histlib
import compiler.lwav_pass.heatgrid as heatlib
import compiler.lwav_pass.vis_util as visutil
import compiler.lwav_pass.table as tbllib
import compiler.lwav_pass.boxandwhisker as boxlib

import compiler.lwav_pass.vis_lscale_stats_util as statsutil
import compiler.lwav_pass.vis_lscale_stats_plots as lscale_plots
import compiler.lwav_pass.vis_lscale_stats_correlations as lscale_corr

import compiler.lscale_pass.lscale_dynsys as lscaleprob
import compiler.lscale_pass.lscale_ops as lscalelib

import hwlib.block as blocklib
import hwlib.device as devlib

from dslang.dsprog import DSProgDB
import numpy as np
import math
import re


def top_circuit_summary(dev,adps):
    names = {
        "qtytau" : "balanced",
        "rand": "single"
    }
    dsprog = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(dsprog.name)

    for (lgraph_id,no_scale,one_mode,scale_method,calib_obj),adp_group in  \
            visutil.adps_groupby(adps,[ADPMetadata.Keys.LGRAPH_ID, \
                                       ADPMetadata.Keys.LSCALE_NO_SCALE, \
                                       ADPMetadata.Keys.LSCALE_ONE_MODE, \
                                       ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                       ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):

        if no_scale or one_mode or scale_method != "phys":
            continue

        if len(adp_group) < 5:
            continue

        rmses = visutil.adps_get_values(adp_group, ADPMetadata.Keys.LWAV_NRMSE)
        total_balanced = len(list(filter(lambda adp: \
                                    adp.metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE) == "qtytau", adp_group)))
        total_random = len(list(filter(lambda adp: \
                                    adp.metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE) == "rand", adp_group)))

        if total_random == 0 or total_balanced == 0:
            continue

        indices = np.argsort(rmses)
        print("----- circuit %d -----" % lgraph_id)

        tbl = tbllib.Tabular(["program","objective","total","rmse", "minimize", "expression"],  \
                             ["%s","%s","%s","%.2e","%s","%s"])
        for rank,idx in enumerate(indices[:5]):
            this_rmse = rmses[idx]
            this_adp = adp_group[idx]
            dsexpr_info= lscaleprob.generate_dynamical_system_info(dev, \
                                                                   dsprog, \
                                                                   this_adp, \
                                                                   apply_scale_transform=False)

            this_count = "%d/%d" % (total_balanced,total_random)
            this_scale_obj = adp_group[idx].metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE)
            this_scale_id = adp_group[idx].metadata.get(ADPMetadata.Keys.LSCALE_ID)
            this_scale_expr = adp_group[idx].metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE_EXPR)
            time_scale_var, ports = statsutil.extract_variables_from_objective_function(dsexpr_info,this_scale_expr)
            if this_scale_obj == "qtytau":
                obj_name = "%s$_{%d}$" % (names[this_scale_obj], this_scale_id)
                tbl.add([dsinfo.name,obj_name,this_count,this_rmse,"",""])
            else:
                if time_scale_var:
                    min_criteria = "\\verbtimescalevar$^{-1}$"
                    expr = ""
                elif this_scale_obj == "rand":
                    assert(len(ports) == 1)
                    inst,port,dsexpr = ports[0]
                    min_criteria = "\\verbmagscalevar{%s}{%s}" % (inst.pretty_print(),port)
                    expr = dsexpr.pretty_print()

                tbl.add([dsinfo.name,names[this_scale_obj],this_count,this_rmse,min_criteria,expr])


        print("------ top scaled adps (calib-obj=%s) ------" % calib_obj)
        print(tbl.render())

    return []
