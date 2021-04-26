import hwlib.adp as adplib
from hwlib.adp import ADP,ADPMetadata

import compiler.lwav_pass.waveform as wavelib
import compiler.lwav_pass.histogram as histlib
import compiler.lwav_pass.heatgrid as heatlib

import compiler.lscale_pass.lscale_dynsys as lscaleprob
import compiler.lscale_pass.lscale_ops as lscalelib

from dslang.dsprog import DSProgDB
import numpy as np
import math

def print_summary(dev,adp):
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = DSProgDB.get_info(program.name)

    print("------------ lscale  ----------------")
    scale_factors = []
    injected_vars = []
    for cfg in adp.configs:
        for stmt in cfg.stmts:
            if stmt.type == adplib.ConfigStmtType.CONSTANT:
                scale_factors.append(stmt.scf)
            if stmt.type == adplib.ConfigStmtType.PORT:
                scale_factors.append(stmt.scf)
            if stmt.type == adplib.ConfigStmtType.EXPR:
                for scf in stmt.scfs:
                    scale_factors.append(scf)
                for inj in stmt.injs:
                    injected_vars.append(inj)

    print("tau=%f" % (adp.tau))
    print("scf total = %d" % len(scale_factors))
    print("scf uniq = %d" % len(set(scale_factors)))
    print("inj total = %d" % len(injected_vars))
    print("inj uniq = %d" % len(set(injected_vars)))
    return []


def correlation_analysis(dev,dsprog,all_adps):

    def get_corr(x,y):
        return np.corrcoef(x,y)[0][1]

    def add_scf(scf_dict,inst,stmt):
        key = (str(inst),stmt.name)
        if not key in scf_dict:
            scf_dict[key] = []

        scf_dict[key].append(stmt.scf)

    lgraph_ids = set(list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LGRAPH_ID], all_adps)))

    for lgraph_id in lgraph_ids:
        adps = list(filter(lambda adp: adp.metadata[ADPMetadata.Keys.LGRAPH_ID] == lgraph_id, \
                           all_adps))

        aqms = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LSCALE_AQM], adps)) 
        dqms = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LSCALE_DQM], adps)) 
        rmses = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LWAV_NRMSE], adps)) 

        taus = list(map(lambda adp: adp.tau, adps))
        scfs =  {}
        for adp in adps:
            dsinfo = lscaleprob.generate_dynamical_system_info(dev,dsprog,adp)
            for cfg in adp.configs:
                for stmt in cfg.stmts:
                    if stmt.type == adplib.ConfigStmtType.CONSTANT:
                        add_scf(scfs,cfg.inst,stmt)
                    if stmt.type == adplib.ConfigStmtType.PORT:
                        if  dsinfo.has_interval(cfg.inst,stmt.name):
                            add_scf(scfs,cfg.inst,stmt)
                        else:
                            print("no interval: %s.%s" % (cfg.inst,stmt.name))

        print("aqm=%s" % get_corr(rmses,aqms))
        print("dqm=%s" % get_corr(rmses,dqms))
        print("tau=%s" % get_corr(rmses,taus))

        print("--- data values correlations ---")
        correlations = []
        scf_idents = list(scfs.keys())
        for (inst,name) in scf_idents:
            curr_scfs = scfs[(inst,name)]
            if len(curr_scfs) != len(rmses):
                print("size mismatch %s" % str(key))
                continue

            corr = get_corr(rmses,curr_scfs)
            if math.isnan(corr):
                corr = 0.0

            correlations.append(corr)

        sorted_indices = np.argsort(list(-1.0*np.abs(correlations)))
        for idx in sorted_indices[:10]:
            inst,name = scf_idents[idx]
            curr_scfs = scfs[(inst,name)]
            corr = correlations[idx]

            ival = dsinfo.get_interval(inst,name)
            expr = dsinfo.get_expr(inst,name) if dsinfo.has_expr(inst,name) else ""
            print("scf %s.%s = %s (%s,%s)" % (inst,name,corr, \
                                            min(curr_scfs),max(curr_scfs)))
            print("   ival=%s expr=%s\n" % (ival,expr))


        input("continue?")

def interval_usage_analysis(dev,dsprog,adps):
    usages = []
    hwinfo = lscalelib.HardwareInfo(dev, \
                                    scale_method=adps[0].metadata.get(ADPMetadata.Keys.LSCALE_SCALE_METHOD), \
                                    calib_obj=adps[0].metadata.get(ADPMetadata.Keys.RUNTIME_CALIB_OBJ), \
                                    one_mode=adps[0].metadata.get(ADPMetadata.Keys.LSCALE_ONE_MODE), \
                                    no_scale=adps[0].metadata.get(ADPMetadata.Keys.LSCALE_NO_SCALE)
    )

    signal_usage_map = []
    coeff_usage_map = []
    for adp in adps:
        dsinfo = lscaleprob.generate_dynamical_system_info(dev,dsprog,adp,apply_scale_transform=True)
        adp_signal_usage_map = []
        adp_coeff_usage_map = []
        for cfg in adp.configs:
            for stmt in cfg.stmts:
                if stmt.type == adplib.ConfigStmtType.CONSTANT:
                    ival = dsinfo.get_interval(cfg.inst, stmt.name)
                    oprng = hwinfo.get_op_range(cfg.inst,cfg.mode,stmt.name)
                    if ival.bound > 0:
                        ratio = ival.bound/oprng.bound
                        adp_coeff_usage_map.append(ratio)

                if stmt.type == adplib.ConfigStmtType.PORT and \
                   dsinfo.has_interval(cfg.inst,stmt.name):
                    ival = dsinfo.get_interval(cfg.inst, stmt.name)
                    oprng = hwinfo.get_op_range(cfg.inst,cfg.mode,stmt.name)
                    ratio = ival.bound/oprng.bound
                    if(ratio > 1.01):
                        expr = dsinfo.get_expr(cfg.inst, stmt.name)
                        print("[warn] %s.%s out of bounds expr=%s ival=%s oprng=%s scf=%s"  \
                                        % (cfg.inst,stmt.name,expr,ival,oprng,stmt.scf))
                    adp_signal_usage_map.append(ratio)

        signal_usage_map.append(adp_signal_usage_map)
        coeff_usage_map.append(adp_coeff_usage_map)

    max_coeff= max(map(lambda vs: max(vs), coeff_usage_map))
    max_sig = max(map(lambda vs: max(vs), signal_usage_map))
    min_coeff= min(map(lambda vs: min(vs), coeff_usage_map))
    min_sig = min(map(lambda vs: min(vs), signal_usage_map))

    port_hg = heatlib.NormalizedHeatGrid('siguse', \
                                         "Signal operating range usage","frac operating range used",10, \
                                         bounds=(min_sig,max_sig))
    datafield_hg = heatlib.NormalizedHeatGrid('valuse',"Constant data field range usage","frac operating range used",10, \
                                              bounds=(min_coeff,max_coeff))
    rmses = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LWAV_NRMSE], adps))
    idxs = np.argsort(rmses)


    for i in idxs:
        vals = list(map(lambda v: (v-min_coeff)/(max_coeff-min_coeff), \
                        coeff_usage_map[i]))
        sigs = list(map(lambda v: (v-min_sig)/(max_sig-min_sig), \
                        signal_usage_map[i]))

        port_hg.add_row(sigs)
        datafield_hg.add_row(vals)

    yield port_hg
    yield datafield_hg

def print_aggregate_summaries(dev,adps,bounds=None):
    adp = adps[0]
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])

    bins = len(adps)/2.0
    aqms = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LSCALE_AQM], adps)) 
    dqms = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LSCALE_DQM], adps)) 
    rmses = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LWAV_NRMSE], adps)) 
    vises = []

    #correlation_analysis(dev,program,adps)
    for vis in interval_usage_analysis(dev,program,adps):
        vises.append(vis)

    correlation_analysis(dev,program,adps)

    meas_color = "#E74C3C"

    vis = histlib.HistogramVis("aqm","aqm",program.name,bins)
    vis.add_data('count',aqms)
    vis.set_style('count',meas_color)
    vises.append(vis)

    vis = histlib.HistogramVis("dqm","dqm",program.name,bins)
    vis.add_data('count',dqms)
    vis.set_style('count',meas_color)
    vises.append(vis)
    return vises
