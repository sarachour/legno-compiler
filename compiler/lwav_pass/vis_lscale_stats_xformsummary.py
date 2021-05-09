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
import compiler.lwav_pass.vis_lscale_stats_bestadp as lscale_bestadp
import compiler.lwav_pass.vis_lscale_stats_xformsummary as lscale_xformsummary

import compiler.lscale_pass.lscale_dynsys as lscaleprob
import compiler.lscale_pass.lscale_ops as lscalelib

import hwlib.block as blocklib
import hwlib.device as devlib

from dslang.dsprog import DSProgDB
import numpy as np
import math
import re


def quality_measure_summary(dev,adps):
    def format_float(min_val,max_val):
        if min_val is None or max_val is None:
            return ""

        if min_val == max_val:
            return "%.2f" % min_val
        else:
            return "%.2f-%.2f" % (min_val,max_val)

    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(program.name)
    for (no_scale,one_mode,scale_method,scale_objective),adp_group in  \
            visutil.adps_groupby(adps,[ADPMetadata.Keys.LSCALE_NO_SCALE, \
                            ADPMetadata.Keys.LSCALE_ONE_MODE, \
                                       ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                       ADPMetadata.Keys.LSCALE_OBJECTIVE]):


        if no_scale or one_mode or scale_objective != "qtytau" or scale_method != "phys":
            continue

        dqms,aqms,dqmes,aqmes,aqm_sts,aqm_derivs,aqm_obses = [],[],[],[],[],[],[]
        for adp in adp_group:
            qual_meas,sig_covs,val_covs,time_coverage = statsutil.get_coverages(dev,program,adp, \
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

        #exp_dqms = visutil.adps_get_values(adp_group, ADPMetadata.Keys.LSCALE_DQME)


        header = ["program","aqm","labels","state vars", "deriv", "obs"]
        tbl = tbllib.Tabular(header, \
                             ["%s"]*len(header))

        row = [dsinfo.name]
        median,iqr,min_val,max_val = visutil.get_statistics(aqms)
        row += [format_float(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(aqmes)
        row += [format_float(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(aqm_sts)
        row += [format_float(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(aqm_derivs)
        row += [format_float(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(aqm_obses)
        row += [format_float(min_val,max_val)]
        tbl.add(row)

        title = "%s / %s" % (scale_method,scale_objective)
        print("===== %s =====" % title)
        print("------ AQM summary ----")
        print(tbl.render())
        print("\n")


        header = ["program","dqm","signals"]
        tbl = tbllib.Tabular(header, \
                             ["%s"]*len(header))

        row = [dsinfo.name]
        median,iqr,min_val,max_val = visutil.get_statistics(dqms)
        row += [format_float(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(dqmes)
        row += [format_float(min_val,max_val)]
        tbl.add(row)
        print("------ DQM summary ----")
        print(tbl.render())
        print("\n")








def scaling_transform_summary(dev,adps):
    def format_int(min_val,max_val):
        if min_val == max_val:
            return "%d" % min_val
        else:
            return "%d-%d" % (min_val,max_val)

    def format_float(min_val,max_val):
        if min_val == max_val:
            return "%.2f" % min_val
        else:
            return "%.2f-%.2f" % (min_val,max_val)


    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(program.name)
    for (no_scale,one_mode,scale_method,scale_objective),adp_group in  \
            visutil.adps_groupby(adps,[ADPMetadata.Keys.LSCALE_NO_SCALE, \
                            ADPMetadata.Keys.LSCALE_ONE_MODE, \
                                       ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                       ADPMetadata.Keys.LSCALE_OBJECTIVE]):


        if no_scale or one_mode or scale_objective != "qtytau" or scale_method != "phys":
            continue



        unique_scale_factors = []
        scale_factors = []
        scale_factor_values = []

        unique_injected = []
        injected = []
        injected_values = []
        taus = []
        for adp in adp_group:
            tau,scfs,injs = statsutil.get_scale_transform(dev,adp)
            taus.append(tau)
            unique_scale_factors.append(len(set(scfs.values())))
            scale_factors.append(len(list(scfs.values())))
            scale_factor_values += list(scfs.values())
            unique_injected.append(len(set(injs.values())))
            injected.append(len(list(injs.values())))
            injected_values += list(injs.values())

        header = ["benchmark", \
                  "tau", \
                  "total", \
                  "unique", \
                  "range", \
                  "total", \
                  "unique", \
                  "range"]

        tbl = tbllib.Tabular(header, \
                            ["%s"]*(len(header)))

        row = [dsinfo.name]
        median,iqr,min_val,max_val = visutil.get_statistics(taus)
        row += [format_float(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(scale_factors)
        row += [format_int(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(unique_scale_factors)
        row += [format_int(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(scale_factor_values)
        row += [format_float(min_val,max_val)]

        median,iqr,min_val,max_val = visutil.get_statistics(injected)
        row += [format_int(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(unique_injected)
        row += [format_int(min_val,max_val)]
        if len(injected_values) > 0:
            median,iqr,min_val,max_val = visutil.get_statistics(injected_values)
            row += [format_float(min_val,max_val)]
        else:
            row += [""]

        tbl.add(row)
        title = "%s / %s" % (scale_method,scale_objective)
        print("===== %s =====" % title)
        print("------ adp scale factor summary ----")
        print(tbl.render())
        print("\n")

