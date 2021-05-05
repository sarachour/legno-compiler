import hwlib.adp as adplib
from hwlib.adp import ADP,ADPMetadata

import compiler.lwav_pass.waveform as wavelib
import compiler.lwav_pass.histogram as histlib
import compiler.lwav_pass.heatgrid as heatlib
import compiler.lwav_pass.vis_util as visutil
import compiler.lwav_pass.table as tbllib
import compiler.lwav_pass.boxandwhisker as boxlib

import compiler.lscale_pass.lscale_dynsys as lscaleprob
import compiler.lscale_pass.lscale_ops as lscalelib

import hwlib.block as blocklib

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

def insert_value(dic,key,val):
    if not key in dic:
        dic[key] = []
    dic[key].append(val)

def get_adp_properties(dev,adp):
    scale_factors = {}
    modes = {}
    for cfg in adp.configs:
        block = dev.get_block(cfg.inst.block)
        key = (cfg.inst)
        modes[key] = cfg.mode

        for stmt in cfg.stmts:
            if stmt.type == adplib.ConfigStmtType.CONSTANT or \
            stmt.type == adplib.ConfigStmtType.PORT:
                key = (cfg.inst,stmt.name)
                scale_factors[key] = stmt.scf

    return scale_factors,modes

def get_coverages(dev,dsprog,adp,  \
                  per_instance=False):
    dsinfo = lscaleprob.generate_dynamical_system_info(dev,dsprog,adp, \
                                                       apply_scale_transform=True)
    signal_coverages = {}
    quality_measures = {}
    max_freq = 1.0/dev.time_constant
    freq_limits = []
    for cfg in adp.configs:
        block = dev.get_block(cfg.inst.block)
        for stmt in cfg.stmts:
            if stmt.type == adplib.ConfigStmtType.CONSTANT or \
            stmt.type == adplib.ConfigStmtType.PORT:
                spec = block.inputs.get(stmt.name) if block.inputs.has(stmt.name) else \
                    (block.outputs.get(stmt.name) if block.outputs.has(stmt.name) else \
                        block.data.get(stmt.name))

                if stmt.type == adplib.ConfigStmtType.PORT:
                    freq_limit = spec.freq_limit.get(cfg.mode)
                    if not freq_limit is None:
                        freq_limits.append(freq_limit)

                if not dsinfo.has_interval(cfg.inst,stmt.name):
                    continue

                ival = dsinfo.get_interval(cfg.inst, stmt.name)
                oprng = spec.interval.get(cfg.mode)
                error = spec.quantize.get(cfg.mode).error(oprng) \
                    if spec.type == blocklib.BlockSignalType.DIGITAL or \
                       isinstance(spec,blocklib.BlockData) else \
                       spec.noise.get(cfg.mode)

                if not per_instance:
                    key = (cfg.inst.block,stmt.name)
                else:
                    key = (cfg.inst,stmt.name)

                if ival.bound > 0:
                    ratio = ival.bound/oprng.bound
                    if not key in signal_coverages:
                        signal_coverages[key] = []

                    signal_coverages[key].append(ratio)

                    if not error is None and error > 0:
                        qm = ival.bound/error
                        if not key in quality_measures:
                            quality_measures[key] = []

                        quality_measures[key].append(qm)

    max_time_scf = min(freq_limits)/max_freq
    time_coverage = (adp.tau)/max_time_scf
    return quality_measures,signal_coverages,time_coverage

def interval_coverage_summary(dev,program,adps):
      def make_new_plot(block,port):
          name = "%s.%s" % (block,port)
          title = "%s %s" % (block,port)
          plt = heatlib.HeatGrid(name=name,title=title,  \
                                 xlabel="% utilization", \
                                 ylabel="% rmse", \
                                 resolution=20)
          plt.numerical_rows = True
          return plt

      for (lgraph_id,no_scale,one_mode,scale_method,scale_objective,calib_obj),adp_group in  \
        visutil.adps_groupby(adps,[ADPMetadata.Keys.LGRAPH_ID, \
                                   ADPMetadata.Keys.LSCALE_NO_SCALE, \
                                   ADPMetadata.Keys.LSCALE_ONE_MODE, \
                                   ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                   ADPMetadata.Keys.LSCALE_OBJECTIVE, \
                                   ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):

        kwargs = visutil.make_plot_kwargs(lgraph_id=lgraph_id, \
                                          no_scale=no_scale, \
                                          one_mode=one_mode, \
                                          scale_method=scale_method, \
                                          scale_objective=scale_objective, \
                                          calib_objective=calib_obj)

        if no_scale or one_mode or len(adp_group) <= 30:
            continue

        #remove outliers
        nadps = len(adp_group)
        rmses =np.array(visutil.adps_get_values(adp_group, ADPMetadata.Keys.LWAV_NRMSE))
        indices = list(range(nadps))
        indices.sort(key=lambda idx:rmses[idx])
        heatmap_plots = {}
        all_heatmap = make_new_plot("all","")

        time_coverages = []
        for idx in indices:
            qual_meas,sig_covs,time_cov= get_coverages(dev,program,adp_group[idx])
            time_coverages.append(time_cov)
            data = []
            for (block,port),coverages in sig_covs.items():
                if block == "fanout" or block == "extin" or block == "extout" or block == "tin" or \
                   block == "tout":
                    continue

                if not (block,port) in heatmap_plots:
                    heatmap_plots[(block,port)] = make_new_plot(block,port)

                heatmap_plots[(block,port)].add_row(sig_covs[(block,port)],value=rmses[idx])
                data += sig_covs[(block,port)]

            all_heatmap.add_row(data,value=rmses[idx])

        tbl = tbllib.Tabular(["metric","min","max","median"], \
                             ["%s","%.2f","%.2f","%.2f"])
        tbl.add(['time coverage',min(time_coverages),max(time_coverages),np.median(time_coverages)])
        print(tbl.render())
        print("\n")


        multi_heatmap = heatlib.MultiHeatGrid("magcov","utilization","% rmse")
        multi_heatmap.add(all_heatmap)
        for (block,port),plot in heatmap_plots.items():
            multi_heatmap.add(plot)

        multi_heatmap.bounds = [0.0,1.0]
        yield kwargs,multi_heatmap

def get_correlation(x,y):
    return np.corrcoef(x,y)[0][1]

def group_by_category(cats,ys):
    by_cat = {}
    for cat,y in zip(cats,ys):
        insert_value(by_cat,cat,y)

    return by_cat


def get_correlation_ratio(cats,ys):
    by_cat = group_by_category(cats,ys)

    mu_pop = np.mean(ys)
    mu_std_cats = []
    std_cats = []
    for cat,y in by_cat.items():
        mu_cat = np.mean(y)
        mu_std_cat = len(y)*(mu_cat - mu_pop)**2
        std_cats += list(map(lambda yi: (yi-mu_pop)**2, y))
        mu_std_cats.append(mu_std_cat)

    variance1 = sum(mu_std_cats)/sum(ys)
    variance2 = sum(std_cats)/sum(ys)
    eta = math.sqrt(variance1/variance2)
    return eta

def covariance_summary(dev,adps,bounds=None):
      for (lgraph_id,no_scale,one_mode,scale_method,scale_objective,calib_obj),adp_group in  \
        visutil.adps_groupby(adps,[ADPMetadata.Keys.LGRAPH_ID, \
                                   ADPMetadata.Keys.LSCALE_NO_SCALE, \
                                   ADPMetadata.Keys.LSCALE_ONE_MODE, \
                                   ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                   ADPMetadata.Keys.LSCALE_OBJECTIVE, \
                                   ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):

        kwargs = visutil.make_plot_kwargs(lgraph_id=lgraph_id, \
                                          no_scale=no_scale, \
                                          one_mode=one_mode, \
                                          scale_method=scale_method, \
                                          scale_objective=scale_objective, \
                                          calib_objective=calib_obj)

        if no_scale or one_mode or len(adp_group) <= 30:
            continue

        dsprog = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
        rmses =visutil.adps_get_values(adp_group, ADPMetadata.Keys.LWAV_NRMSE)
        aqms =visutil.adps_get_values(adp_group, ADPMetadata.Keys.LSCALE_AQM)
        dqms =visutil.adps_get_values(adp_group, ADPMetadata.Keys.LSCALE_DQM)
        tcs = list(map(lambda adp: adp.tau, adp_group))

        print("--- time constants ---")
        tbl = tbllib.Tabular(["metric","min","max","median","correlation (with rmse)"], \
                             ["%s","%.2f","%.2f","%.2f","%.3f"])
        corr = get_correlation(aqms,rmses)
        tbl.add(['aqm',min(aqms),max(aqms),np.median(aqms),corr])
        corr = get_correlation(dqms,rmses)
        tbl.add(['dqm',min(dqms),max(dqms),np.median(dqms),corr])
        corr = get_correlation(tcs,rmses)
        tbl.add(['tc',min(tcs),max(tcs),np.median(tcs),corr])
        print(tbl.render())
        print("\n")


        all_scfs = {}
        all_qms = {}
        all_exprs = {}
        all_modes = {}


        for adp in adp_group:
            dsexprs = lscaleprob.generate_dynamical_system_info(dev, \
                                                                dsprog,adp, \
                                                                apply_scale_transform=False)
            qual_meas,sig_covs,_= get_coverages(dev,dsprog,adp,per_instance=True)

            scfs,modes = get_adp_properties(dev,adp)
            for key,scf in scfs.items():
                insert_value(all_scfs,key,scf)
                if key in qual_meas:
                    assert(len(qual_meas[key]) == 1)
                    insert_value(all_qms,key,qual_meas[key][0])

                if dsexprs.has_expr(*key):
                    insert_value(all_exprs,key,dsexprs.get_expr(*key))

            for key,mode in modes.items():
                insert_value(all_modes,key,mode)

        tbl = tbllib.Tabular(["block","port","expr","scale factor corr.","quality measure corr."], \
                             ["%s","%s","%s","%.2f", "%.2f"])

        tbl.sort_by('expr')
        for key in all_exprs.keys():
            scfs = all_scfs[key]
            inst,port = key
            scf_corr = get_correlation(scfs,rmses)
            expr = all_exprs[(key[0],key[1])][0]
            if key in all_qms:
                qms = all_qms[key]
                qm_corr = get_correlation(qms,rmses)
                tbl.add([inst,port,expr.pretty_print(), scf_corr,qm_corr])


        print(tbl.render())
        print("\n")

        return []


def print_compensation_comparison(adps):
    series = {
        ("ideal","minimize_error"): "ideal",
        ("phys","minimize_error"): "minerr",
        ("phys","maximize_fit"): "maxfit"
    }
    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(program.name)
    for (lgraph_id,no_scale,one_mode,scale_objective),adp_group in  \
        visutil.adps_groupby(adps,[ADPMetadata.Keys.LGRAPH_ID,  \
                           ADPMetadata.Keys.LSCALE_NO_SCALE, \
                           ADPMetadata.Keys.LSCALE_ONE_MODE, \
                           ADPMetadata.Keys.LSCALE_OBJECTIVE]):

        kwargs = visutil.make_plot_kwargs(lgraph_id=lgraph_id, \
                                  no_scale=no_scale, one_mode=one_mode, \
                                  scale_objective=scale_objective) 

        dataset = {}
        for (scale_method,calib_obj), plot_adps in visutil.adps_groupby(adp_group, \
                                                     [ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                                                      ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):

            values = visutil.adps_get_values(plot_adps, ADPMetadata.Keys.LWAV_NRMSE)
            series_name = series[(scale_method,calib_obj)]
            dataset[series_name] = values


        series_order = ["ideal","minerr","maxfit"]
        if any(map(lambda ser: not ser in dataset, series_order)):
            continue

        boxwhisk = boxlib.BoxAndWhiskerVis('compensate', \
                                           xaxis='compensation method',
                                           yaxis='% rmse',
                                           title='%s' % dsinfo.name)
        boxwhisk.show_outliers = False
        for ser in series_order:
            boxwhisk.add_data(ser,dataset[ser])

        yield kwargs,boxwhisk

def print_random_comparison(adps):
    adp = adps[0]
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])

    series = {
        'qtytau': 'balanced',
        'qty': 'quality',
        'rand':'random'
    }
    for (lgraph_id,no_scale,one_mode,scale_method,calib_obj),adp_group in  \
        visutil.adps_groupby(adps,[ADPMetadata.Keys.LGRAPH_ID,  \
                           ADPMetadata.Keys.LSCALE_NO_SCALE, \
                           ADPMetadata.Keys.LSCALE_ONE_MODE, \
                           ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                           ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):

        kwargs = visutil.make_plot_kwargs(lgraph_id=lgraph_id, \
                                  no_scale=no_scale, one_mode=one_mode, \
                                  scale_method=scale_method, \
                                  calib_objective=calib_obj)


        dataset = {}
        for (scale_objective,), plot_adps in visutil.adps_groupby(adp_group, \
                                                     [ADPMetadata.Keys.LSCALE_OBJECTIVE]):
            values = visutil.adps_get_values(plot_adps, ADPMetadata.Keys.LWAV_NRMSE)
            series_name = series[scale_objective]
            dataset[series_name] = values


        series_order = ["balanced","random"]
        if any(map(lambda ser: not ser in dataset, series_order)):
            continue

        boxwhisk = boxlib.BoxAndWhiskerVis('rand', \
                                           xaxis='calibration objective',\
                                           yaxis='% rmse',
                                           title='%s' % program)

        boxwhisk.draw_minimum = True
        boxwhisk.show_outliers = False
        for ser in series_order:
            boxwhisk.add_data(ser,dataset[ser])
        yield kwargs, boxwhisk


def print_aggregate_summaries(dev,adps,bounds=None):
    adp = adps[0]
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])

    bins = len(adps)/2.0
    aqms = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LSCALE_AQM], adps)) 
    dqms = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LSCALE_DQM], adps)) 
    rmses = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LWAV_NRMSE], adps)) 
    vises = []

    for kwargs,vis in print_compensation_comparison(adps):
        vises.append((kwargs,vis))


    for kwargs,vis in interval_coverage_summary(dev,program,adps):
        vises.append((kwargs,vis))

    for kwargs,vis in print_random_comparison(adps):
        vises.append((kwargs,vis))


    covariance_summary(dev,adps)
    return vises
