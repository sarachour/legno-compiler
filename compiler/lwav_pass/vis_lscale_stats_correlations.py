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


def get_quality_correlation(qms, rmses):
        if all(map(lambda q: q is None, qms)):
            return ""
        else:
            return "%.2f" % statsutil.get_correlation(qms,rmses)

def quality_correlation_summary(dev,adps):
    dsprog = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(dsprog.name)

    for (lgraph_id,no_scale,one_mode,calib_obj,scale_method),adp_group in  \
            visutil.adps_groupby(adps,[ADPMetadata.Keys.LGRAPH_ID, \
                                       ADPMetadata.Keys.LSCALE_NO_SCALE, \
                                       ADPMetadata.Keys.LSCALE_ONE_MODE, \
                                       ADPMetadata.Keys.RUNTIME_CALIB_OBJ, \
                                       ADPMetadata.Keys.LSCALE_SCALE_METHOD]):

        if no_scale or one_mode or scale_method != "phys":
            continue

        rmses = visutil.adps_get_values(adp_group, ADPMetadata.Keys.LWAV_NRMSE)
        total_balanced = len(list(filter(lambda adp: \
                                    adp.metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE) == "qtytau", adp_group)))
        total_random = len(list(filter(lambda adp: \
                                    adp.metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE) == "rand", adp_group)))

        if total_balanced == 0 or total_random == 0:
            continue

        dqms,aqms,dqmes,aqmes,aqm_sts,aqm_derivs,aqm_obses = [],[],[],[],[],[],[]
        aqms = []
        dqmes = []
        aqmes = []
        aqm_sts = []
        aqm_derivs= []
        aqm_obses = []
        speeds = []
        print("-> deriving quality measures")
        for adp in adp_group:
            qual_meas,sig_covs,val_covs,time_coverage = statsutil.get_coverages(dev,dsprog,adp, \
                                                                                per_instance=True, \
                                                                                apply_scale_transform=True)
            aqm, dqm, aqme,dqme,aqm_st,aqm_deriv,aqm_obs = statsutil.get_aggregate_quality_measures(dev,adp,qual_meas)
            aqms.append(aqm)
            dqms.append(dqm)
            aqmes.append(aqme)
            dqmes.append(dqme)
            aqm_sts.append(aqm_st)
            aqm_derivs.append(aqm_deriv)
            aqm_obses.append(aqm_obs)
            speeds.append(adp.tau)

        tbl = tbllib.Tabular(["program","speed","dqm","aqm","dqme","aqm (labels)","aqm (state vars)", "aqm (deriv)", "aqm (obs)"], \
                             ["%s", "%s","%s", "%s","%s","%s","%s","%s","%s"])
        row = [dsinfo.name]
        corr = get_quality_correlation(speeds,rmses)
        row.append(corr)
        corr = get_quality_correlation(dqms,rmses)
        row.append(corr)
        corr = get_quality_correlation(aqms,rmses)
        row.append(corr)
        corr = get_quality_correlation(dqmes,rmses)
        row.append(corr)
        corr = get_quality_correlation(aqmes,rmses)
        row.append(corr)
        corr = get_quality_correlation(aqm_sts,rmses)
        row.append(corr)
        corr = get_quality_correlation(aqm_derivs,rmses)
        row.append(corr)
        corr = get_quality_correlation(aqm_obses,rmses)
        row.append(corr)

        tbl.add(row)
        print("----- quality correlations (%s,%d) -----" % (calib_obj,lgraph_id))
        print(tbl.render())
        print("\n")



def signal_correlation_summary(dev,adps):
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

        total_balanced = len(list(filter(lambda adp: \
                                    adp.metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE) == "qtytau", adp_group)))
        total_random = len(list(filter(lambda adp: \
                                    adp.metadata.get(ADPMetadata.Keys.LSCALE_OBJECTIVE) == "rand", adp_group)))

        if total_balanced == 0 or total_random == 0:
            continue


        signal_coverages = {}
        signal_rmses = {}
        value_coverages = {}
        value_rmses = {}
        time_coverages = []

        rmses = visutil.adps_get_values(adp_group, ADPMetadata.Keys.LWAV_NRMSE)

        for rmse,adp in zip(rmses,adp_group):
            qual_meas,sig_covs,val_covs,time_coverage = statsutil.get_coverages(dev,dsprog,adp, \
                                                                      per_instance=True, \
                                                                      apply_scale_transform=True)
            unscaled_adp = visutil.get_unscaled_adp(dev,adp)
            dsinfo= lscaleprob.generate_dynamical_system_info(dev, \
                                                              dsprog, \
                                                              unscaled_adp, \
                                                              apply_scale_transform=False)

            time_coverages.append(time_coverage)
            for (inst,port),coverage in sig_covs.items():
                key = dsinfo.get_expr(inst,port)
                statsutil.insert_value(signal_coverages, key, coverage[0])
                statsutil.insert_value(signal_rmses, key, rmse)

            for (inst,port),coverage in sig_covs.items():
                key = dsinfo.get_expr(inst,port)
                statsutil.insert_value(value_coverages, key, coverage[0])
                statsutil.insert_value(value_rmses, key, rmse)

        if len(rmses) == 0:
            continue

        tbl = tbllib.Tabular(["signal","corr","abs(corr)"],[ "%s", "%.2f","%.2f"])
        for expr, coverages in signal_coverages.items():
            corr = statsutil.get_correlation(coverages,signal_rmses[expr])
            tbl.add([expr,corr,-abs(corr)])

        tbl.sort_by("abs(corr)")
        print("------ signal correlations (%d,%s) ------" % (lgraph_id,calib_obj))
        print(tbl.render())
        print("\n")

        tbl = tbllib.Tabular(["value","corr","abs(corr)"], ["%s", "%.2f","%.2f"]) 
        tbl.sort_by("abs(corr)")
        for expr, coverages in value_coverages.items():
            corr = statsutil.get_correlation(coverages,value_rmses[expr])
            tbl.add([expr,corr,-abs(corr)])

        print("----- value correlations (%d,%s) ------" % (lgraph_id,calib_obj))
        print(tbl.render())
        print("\n")

        corr = statsutil.get_correlation(time_coverages,rmses)
        print("------ time correlations (%d,%s) ------" % (lgraph_id,calib_obj))
        print("correlation=%.2f" % corr)
        print("\n\n")

