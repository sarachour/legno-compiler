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


def signal_coverage_summary(dev,adps):
    def fmtutilize(val):
        if abs(val -100.0) < 1e-5:
            return "\\textbf{%.1f}" % val
        else:
            return "%.1f"% val

    def format_int(min_val,max_val):
        if min_val == max_val:
            return "%d" % min_val
        else:
            return "%d-%d" % (min_val,max_val)

    def format_float(min_val,max_val):
        if abs(min_val - max_val) < 1e-2:
            return "%s" % (fmtutilize(min_val*100.0))
        else:
            return "%s-%s" % (fmtutilize(min_val*100.0),fmtutilize(max_val*100.0))

    def format_statistics(values):
        med = list(map(lambda v: np.median(v), values))
        iqr = list(map(lambda v: np.percentile(v,75) - np.percentile(v,25), values))
        minval = list(map(lambda v: min(v), values))
        maxval = list(map(lambda v: max(v), values))
        return [ \
                 format_float(min(med),max(med)), \
                 format_float(min(iqr),max(iqr)), \
                 format_float(min(minval),max(minval)), \
                 format_float(min(maxval),max(maxval)), \
        ]

    dsprog = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(dsprog.name)

    for (no_scale,one_mode,scale_method,scale_objective),adp_group in  \
            visutil.adps_groupby(adps,[ADPMetadata.Keys.LSCALE_NO_SCALE, \
                            ADPMetadata.Keys.LSCALE_ONE_MODE, \
                                       ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                       ADPMetadata.Keys.LSCALE_OBJECTIVE]):


        if no_scale or one_mode  \
           or scale_objective != "qtytau"  \
               or scale_method != "phys":
            continue

        unscaled_time_coverages = []
        scaled_time_coverages = []
        unscaled_signal_coverages = []
        unscaled_value_coverages = []
        scaled_signal_coverages = []
        scaled_value_coverages = []
        for adp in adp_group:
            prescale = 0.95
            qual_meas,sig_covs,val_covs,time_coverage = statsutil.get_coverages(dev,dsprog,adp, \
                                                                                per_instance=True, \
                                                                                apply_scale_transform=True, \
                                                                                prescale=prescale)
            oobs = list(filter(lambda v: v[0] - 1.0 > 1e-5,sig_covs.values()))
            if len(oobs) > 0:
                for oob in oobs:
                    print("out-of-bounds: %s" % oob)
                print("--")
                continue

            median,iqr,min_val,max_val = visutil.get_statistics(list(sig_covs.values()))
            scaled_signal_coverages.append(list(map(lambda v: v[0], sig_covs.values())))
            scaled_value_coverages.append(list(map(lambda v: v[0], val_covs.values())))
            scaled_time_coverages.append(time_coverage)

            qual_meas,sig_covs,val_covs,time_coverage = statsutil.get_coverages(dev,dsprog,adp, \
                                                                                per_instance=True, \
                                                                                apply_scale_transform=False, \
                                                                                prescale=prescale)
            unscaled_signal_coverages.append(list(map(lambda v: v[0], sig_covs.values())))
            unscaled_value_coverages.append(list(map(lambda v: v[0], val_covs.values())))
            unscaled_time_coverages.append(time_coverage)

        title = "%s / %s" % (scale_method,scale_objective)
        print("##################################")
        print("=====                  %s                      =====" % title)
        print("##################################")
        if len(scaled_signal_coverages) == 0:
            continue

        header = ["benchmark","type","scaled","median","iqr","min","max"]
        tbl = tbllib.Tabular(header, \
                             ["%s"]*(len(header)))

        row = [dsinfo.name, "signal","unscale"]
        row += format_statistics(unscaled_signal_coverages)
        tbl.add(row)

        row = [dsinfo.name, "signal","scale"]
        row += format_statistics(scaled_signal_coverages)
        tbl.add(row)

        row = [dsinfo.name,"value", "unscale"]
        row += format_statistics(unscaled_value_coverages)
        tbl.add(row)

        row = [dsinfo.name,"value", "scale"]
        row += format_statistics(scaled_value_coverages)
        tbl.add(row)
        print("------ adp value summary ----")
        print(tbl.render())
        print("\n")


        header = ["benchmark","type","median","iqr","min","max"]
        tbl = tbllib.Tabular(header, \
                             ["%s"]*len(header))
        median,iqr,minval,maxval = visutil.get_statistics(scaled_time_coverages)
        median,iqr,minval,maxval = visutil.get_statistics(unscaled_time_coverages)
        row = [dsinfo.name,"unsc"]
        row += format_statistics([unscaled_time_coverages])
        tbl.add(row)
        row = [dsinfo.name,"sc"]
        row += format_statistics([scaled_time_coverages])
        tbl.add(row)
        print("------ time summary ----")
        print(tbl.render())
        print("\n")

