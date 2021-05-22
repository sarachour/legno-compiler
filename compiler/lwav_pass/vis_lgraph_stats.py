import hwlib.adp as adplib
from hwlib.adp import ADP,ADPMetadata
import hwlib.block as blocklib

import compiler.lscale_pass.lscale_dynsys as lscaleprob
import compiler.lscale_pass.lscale_ops as  lscalelib
import compiler.lsim as lsimlib

import compiler.lwav_pass.waveform as wavelib
import compiler.lwav_pass.histogram as histlib
import compiler.lwav_pass.heatgrid as heatlib
import compiler.lwav_pass.scatter as scatlib
import compiler.lwav_pass.boxandwhisker as boxlib
import compiler.lwav_pass.vis_util as vislib
import compiler.lwav_pass.table as tbllib

from dslang.dsprog import DSProgDB
import ops.generic_op as genoplib
import ops.base_op as baseoplib
import numpy as np
import math
import util.paths as paths
import json

def print_lgraph_comparison(adps):
    adp = adps[0]
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(program.name)

    if not vislib.has_waveforms(adps):
        return

    # compute upper bound for all plots
    for (no_scale,one_mode,scale_method,scale_objective),adp_super_group in  \
        vislib.adps_groupby(adps,[ADPMetadata.Keys.LSCALE_NO_SCALE, \
                           ADPMetadata.Keys.LSCALE_ONE_MODE, \
                           ADPMetadata.Keys.LSCALE_SCALE_METHOD, \
                           ADPMetadata.Keys.LSCALE_OBJECTIVE]):

        if no_scale or one_mode:
            continue

        max_nrmses = []
        for (calib_obj,lgraph_id,), plot_adps in vislib.adps_groupby(adp_super_group, \
                                                        [ADPMetadata.Keys.RUNTIME_CALIB_OBJ, \
                                                         ADPMetadata.Keys.LGRAPH_ID]):
                values = vislib.adps_get_values(plot_adps, ADPMetadata.Keys.LWAV_NRMSE)
                q3,q1 = np.percentile(values,75),np.percentile(values,25)
                iqr = q3-q1
                fence = q3+1.5*iqr
                max_nrmses.append(max(filter(lambda v: v < fence, values)))

        max_nrmse = max(max_nrmses)

        # plot figures
        for (calib_obj,),adp_group in  \
            vislib.adps_groupby(adp_super_group,[ADPMetadata.Keys.RUNTIME_CALIB_OBJ]):

            kwargs = vislib.make_plot_kwargs(no_scale=no_scale, \
                                            one_mode=one_mode, \
                                            scale_method=scale_method, \
                                            scale_objective=scale_objective, \
                                            calib_objective=calib_obj)

            if no_scale or one_mode:
                continue

            if scale_objective == lscalelib.ObjectiveFun.RANDOM:
                continue

            dataset = {}
            for (lgraph_id,), plot_adps in vislib.adps_groupby(adp_group, \
                                                        [ADPMetadata.Keys.LGRAPH_ID]):
                values = vislib.adps_get_values(plot_adps, ADPMetadata.Keys.LWAV_NRMSE)
                dataset[lgraph_id] = values

            if len(dataset) <= 1:
                continue

            series_order = list(dataset.keys())
            series_order.sort()

            boxwhisk = boxlib.BoxAndWhiskerVis('lgraph', \
                                            xaxis='generated circuit',\
                                            yaxis='% rmse',
                                            title='%s' % dsinfo.name)

            boxwhisk.set_bounds(0,max_nrmse*1.05)
            #boxwhisk.draw_minimum = True
            boxwhisk.show_outliers = False
            boxwhisk.show_xlabel = False
            for ser in series_order:
                boxwhisk.add_data(ser,dataset[ser])
            yield kwargs, boxwhisk



def circuit_block_distribution_summary(dev,adps):
    def format_cell(lst):
        if min(lst) == max(lst):
            return "%d" % lst[0]
        else:
            return "%d-%d" % (min(lst),max(lst))

    blocks = ['mult','integ', 'adc','dac','lut', 'fanout','extout','cin','cout','tin','tout']

    block_counts = dict(map(lambda blk: (blk,[]), blocks))
    block_modes = dict(map(lambda blk: (blk,[]), blocks))
    block_totals = []
    conn_totals = []
    kirch_totals = []

    for adp in adps:
        by_block = dict(map(lambda blk: (blk,[]), blocks))
        for cfg in adp.configs:
            if cfg.inst.block in by_block:
                by_block[cfg.inst.block].append(cfg.mode)

        kirchs = []
        for conn in adp.conns:
            for conn2 in adp.conns:
                if conn.same_dest(conn2) and \
                   not conn.same_source(conn2):
                    kirchs.append((conn.dest_inst,conn.dest_port))

        for blk,modes in by_block.items():
            block_counts[blk].append(len(modes))
            block_modes[blk].append(set(modes))

        conn_totals.append(len(list(adp.conns)))
        block_totals.append(len(list(adp.configs)))
        kirch_totals.append(len(set(kirchs)))

    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(program.name)

    header = ["benchmark","blocks","conns"] + blocks+['kirch']
    tbl = tbllib.Tabular(header, \
                         ["%s"]*len(header))

    row = []
    row.append(dsinfo.name)
    row.append(format_cell(block_totals))
    row.append(format_cell(conn_totals))
    for block_name,cnts in block_counts.items():
        row.append(format_cell(cnts))

    row.append(format_cell(kirch_totals))
    tbl.add(row)

    print("------ block count row ------")
    print(tbl.render())
    print("\n")



def circuit_block_equation_summary(dev,adps):
    def get_expr(adp,dsinfo,inst,port):
        block = dev.get_block(inst.block)
        mode = adp.configs.get(inst.block,inst.loc).modes[0]
        rel = block.outputs[port].relation[mode] if block.outputs.has(port) \
            else None

        if block.outputs.has(port):
            rel = lscaleprob.get_output_relation(dev,adp,inst, \
                                                 port, \
                                                 apply_scale_transform=False)
            inputs = {}
            for var in rel.vars():
                inputs[var] = dsinfo.get_expr(inst,var)
            return  rel.substitute(inputs)

        else:
            rel = lscaleprob.get_input_relation(dsinfo,dev,adp,inst, \
                                                 port, \
                                                 apply_scale_transform=False)
            return  rel

    if not vislib.has_waveforms(adps):
        return

    rmses = vislib.adps_get_values(adps,ADPMetadata.Keys.LWAV_NRMSE)
    idx = np.argmin(rmses)

    adp = vislib.get_unscaled_adp(dev,adps[idx])

    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = lscaleprob.generate_dynamical_system_info(dev,program,adp, \
                                                       apply_scale_transform=False, \
                                                       label_integrators_only=False)


    print("------------ equations ---------------")
    for var in program.variables():
        sources = adp.get_by_source(genoplib.Var(var))
        exprs = list(map(lambda src: get_expr(adp,dsinfo,src[0],src[1]), sources))
        valid_exprs = list(filter(lambda e: not set(e.vars()) == set([var])  or \
                                  e.has_op(baseoplib.OpType.INTEG), exprs))
        if len(valid_exprs) == 0:
            raise Exception("could not identify variable expression <%s> %s / %s" % (var,exprs,sources))

        expr = valid_exprs[0]
        clauses = genoplib.break_expr_string(expr.pretty_print())
        lhs = genoplib.Var(var,latex_style="\\rvar{%s}")
        print("%s = %s" % (lhs.pretty_print(),"\n\t".join(clauses)))
    print("\n\n")

    print("--------- adp ---------------")
    print(adp.to_latex())
    print("\n\n")

    return []



def runtime_summary(adps):
    program = DSProgDB.get_prog(adps[0].metadata[ADPMetadata.Keys.DSNAME])
    dsinfo = DSProgDB.get_info(program.name)

    if not adps[0].metadata.has(adplib.ADPMetadata.Keys.LGRAPH_SYNTH_RUNTIME):
        return

    synth_time = adps[0].metadata.get(adplib.ADPMetadata.Keys.LGRAPH_SYNTH_RUNTIME)
    asm_runtimes = vislib.adps_get_values(adps, ADPMetadata.Keys.LGRAPH_ASM_RUNTIME)
    route_runtimes = vislib.adps_get_values(adps, ADPMetadata.Keys.LGRAPH_ROUTE_RUNTIME)

    header = ["benchmark","time", "median","iqr","min","max", "median","iqr","min","max"]
    tbl = tbllib.Tabular(header, \
                         ["%s"]+ ["%.2f"]*(len(header)-1))

    row = []
    row.append(dsinfo.name)
    row.append(synth_time)
    median,iqr,min_val,max_val = vislib.get_statistics(asm_runtimes)
    row += [median,iqr,min_val,max_val]
    median,iqr,min_val,max_val = vislib.get_statistics(route_runtimes)
    row += [median,iqr,min_val,max_val]
    tbl.add(row)

    print(tbl.render())
    print("\n")

    print("----- fragment synthesis breakdown ----")
    synth_times_by_variable = adps[0].metadata.get(adplib.ADPMetadata.Keys.LGRAPH_SYNTH_RUNTIME_BY_VAR)
    by_variable = json.loads(synth_times_by_variable)

    header = [dsinfo.name] + ['median','iqr','min','max']
    tbl = tbllib.Tabular(header, \
                         ["%s"]+ ["%.4f"]*(len(header)))
    for variable,runts in by_variable.items():
        median,iqr,min_val,max_val = vislib.get_statistics(runts)
        tbl.add([variable]+[median,iqr,min_val,max_val])

    tbl_trans = tbl.transpose()
    print("----- lgraph runtime breakdown -----")
    print(tbl_trans.render())
    print("\n")



def print_aggregate_summaries(dev,args,adps):
    vises = []

    if args.lgraph_rmse_plots:
        for kwargs,vis in print_lgraph_comparison(adps):
            vises.append((kwargs,vis))

    if args.equations:
        circuit_block_equation_summary(dev,adps)

    if args.lgraph_static:
        circuit_block_distribution_summary(dev,adps)

    if args.compile_times:
        runtime_summary(adps)

    return vises
