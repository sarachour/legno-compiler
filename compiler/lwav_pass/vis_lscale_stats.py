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



def quality_measure_summary(dev,adps):

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


        aqms = visutil.adps_get_values(adp_group, ADPMetadata.Keys.LSCALE_AQM)
        dqms = visutil.adps_get_values(adp_group, ADPMetadata.Keys.LSCALE_DQM)
        st_aqms = visutil.adps_get_values(adp_group, ADPMetadata.Keys.LSCALE_AQMST)
        obs_aqms = visutil.adps_get_values(adp_group, ADPMetadata.Keys.LSCALE_AQMOBS)
        #exp_dqms = visutil.adps_get_values(adp_group, ADPMetadata.Keys.LSCALE_DQME)


        header = ["benchmark", \
                  "aqms", \
                  "dqms", \
                "aqms (stvar)", \
                "aqms (obs)"]

        row = [dsinfo.name]
        median,iqr,min_val,max_val = visutil.get_statistics(aqms)
        row += [format_float(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(dqms)
        row += [format_float(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(st_aqms)
        row += [format_float(min_val,max_val)]
        median,iqr,min_val,max_val = visutil.get_statistics(obs_aqms)
        row += [format_float(min_val,max_val)]


        tbl = tbllib.Tabular(header, \
                            ["%s"]*(len(header)))
        tbl.add(row)

        title = "%s / %s" % (scale_method,scale_objective)
        print("===== %s =====" % title)
        print("------ adp quality summary ----")
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


def signal_coverage_summary(dev,adps):
    def format_int(min_val,max_val):
        if min_val == max_val:
            return "%d" % min_val
        else:
            return "%d-%d" % (min_val,max_val)

    def format_float(min_val,max_val):
        if min_val == max_val:
            return "%.1f" % (min_val*100.0)
        else:
            return "%.1f-%.1f" % (min_val*100.0,max_val*100.0)

    def format_statistics(values):
        med = list(map(lambda v: np.median(v), values))
        iqr = list(map(lambda v: np.percentile(v,75) - np.percentile(v,25), values))
        minval = min(list(map(lambda v: min(v), values)))
        maxval = max(list(map(lambda v: max(v), values)))
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


        if no_scale or one_mode or scale_objective != "qtytau" or scale_method != "phys":
            continue

        time_coverages = []
        unscaled_signal_coverages = []
        unscaled_value_coverages = []
        scaled_signal_coverages = []
        scaled_value_coverages = []
        for adp in adp_group:

            qual_meas,sig_covs,val_covs,time_coverage = statsutil.get_coverages(dev,dsprog,adp, \
                                                                      per_instance=True, \
                                                                      apply_scale_transform=False)
            unscaled_signal_coverages.append(list(sig_covs.values()))
            unscaled_value_coverages.append(list(val_covs.values()))

            qual_meas,sig_covs,val_covs,time_coverage = statsutil.get_coverages(dev,dsprog,adp, \
                                                                      per_instance=True, \
                                                                      apply_scale_transform=True)
            median,iqr,min_val,max_val = visutil.get_statistics(list(sig_covs.values()))
            scaled_signal_coverages.append(list(sig_covs.values()))
            scaled_value_coverages.append(list(val_covs.values()))
            time_coverages.append(time_coverage)

        title = "%s / %s" % (scale_method,scale_objective)
        print("===== %s =====" % title)


        header = ["benchmark","type"] + ["median","iqr","min","max"]*2
        tbl = tbllib.Tabular(header, \
                             ["%s"]*(len(header)))

        row = [dsinfo.name, "unsc"]
        row += format_statistics(unscaled_signal_coverages)
        row += format_statistics(unscaled_value_coverages)
        tbl.add(row)

        row = [dsinfo.name, "sc"]
        row += format_statistics(scaled_signal_coverages)
        row += format_statistics(scaled_value_coverages)
        tbl.add(row)
        print("------ adp scale factor summary ----")
        print(tbl.render())
        print("\n")

        header = ["benchmark","median","iqr","min","max"]
        tbl = tbllib.Tabular(header, \
                            ["%s","%.1f","%.1f","%.1f","%.1f"])
        median,iqr,minval,maxval = visutil.get_statistics(time_coverages)
        row = [dsinfo.name]
        row += [100*median,100*iqr,100*minval,100*maxval]
        tbl.add(row)
        print("------ time summary ----")
        print(tbl.render())
        print("\n")


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
def print_aggregate_summaries(dev,adps,bounds=None):

    quality_measure_summary(dev,adps)
    scaling_transform_summary(dev,adps)
    signal_coverage_summary(dev,adps)
    lscale_corr.signal_correlation_summary(dev,adps)
    lscale_corr.quality_correlation_summary(dev,adps)
    top_circuit_summary(dev,adps)

    vises = []
    for kwargs,vis in lscale_plots.print_compensation_comparison(adps):
        vises.append((kwargs,vis))


    for kwargs,vis in lscale_plots.print_random_comparison(adps):
        vises.append((kwargs,vis))


    #covariance_summary(dev,adps)
    return vises
