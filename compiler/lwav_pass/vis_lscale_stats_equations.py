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
import compiler.lwav_pass.vis_lscale_stats_xformsummary as lscale_xform
import compiler.lwav_pass.vis_lscale_stats_signalusage as lscale_signalusage
import compiler.lwav_pass.vis_lscale_stats_equations as lscale_equations
import compiler.lwav_pass.vis_util as vislib

import compiler.lscale_pass.lscale_dynsys as lscaleprob
import compiler.lscale_pass.lscale_ops as lscalelib

import runtime.models.exp_delta_model as deltalib

import hwlib.block as blocklib
import hwlib.device as devlib
import hwlib.hcdc.llenums as llenums

import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
import ops.base_op as baseoplib


from dslang.dsprog import DSProgDB
import numpy as np
import math
import re


def get_valid_adps(adps):
    valid = []
    for adp in adps:
        if adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE) == "rand" or \
           adp.metadata.get(adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD) != "phys":
            continue

        valid.append(adp)

    return valid

def scaled_expression_simplify(expr):
    if expr.op == baseoplib.OpType.MULT:
        arg1 = scaled_expression_simplify(expr.arg1)
        arg2 = scaled_expression_simplify(expr.arg2)
        if arg1.op == baseoplib.OpType.CONST and \
           arg1.value == 1.0:
            return arg2

        if arg2.op == baseoplib.OpType.CONST and \
           arg2.value == 1.0:
            return arg1

        return genoplib.Mult(arg1,arg2)

    elif expr.op == baseoplib.OpType.ADD:
        arg1 = scaled_expression_simplify(expr.arg1)
        arg2 = scaled_expression_simplify(expr.arg2)
        return genoplib.Add(arg1,arg2)

    elif expr.op == baseoplib.OpType.INTEG:
        arg1 = scaled_expression_simplify(expr.deriv)
        arg2 = scaled_expression_simplify(expr.init_cond)
        return genoplib.Integ(arg1,arg2)

    elif expr.op == baseoplib.OpType.EMIT:
        arg1 = scaled_expression_simplify(expr.arg(0))
        return genoplib.Emit(arg1)

    elif expr.op == baseoplib.OpType.POW:
        arg1 = scaled_expression_simplify(expr.arg1)
        arg2 = scaled_expression_simplify(expr.arg2)
        return lambdoplib.Pow(arg1,arg2)

    elif expr.op == baseoplib.OpType.SGN:
        arg1 = scaled_expression_simplify(expr.arg(0))
        return lambdoplib.Sgn(arg1)

    elif expr.op == baseoplib.OpType.ABS:
        arg1 = scaled_expression_simplify(expr.arg(0))
        return lambdoplib.Abs(arg1)


    elif expr.op == baseoplib.OpType.SIN:
        arg1 = scaled_expression_simplify(expr.arg(0))
        return lambdoplib.Sin(arg1)


    else:
        return expr


def delta_model_summary(dev,all_adps):
    def get_model(cfg,output):
        mdls = deltalib.get_models(dev,  \
                                   clauses=[ \
                                             deltalib.ExpDeltaModelClause.BLOCK, \
                                             deltalib.ExpDeltaModelClause.LOC, \
                                             deltalib.ExpDeltaModelClause.OUTPUT, \
                                             deltalib.ExpDeltaModelClause.STATIC_CONFIG, \
                                             deltalib.ExpDeltaModelClause.CALIB_OBJ
                                   ], \
                                   block=block, \
                                   loc=cfg.inst.loc, \
                                   output=output, \
                                   config=cfg, \
                                   calib_obj = calib_obj )
        if len(mdls) == 0:
            return None
        elif len(mdls) == 1:
            mdl = mdls[0]
            return mdl
        else:
            for mdl in mdls:
                print(mdl)
            raise Exception("only one delta model expected")

    adps = get_valid_adps(all_adps)
    rmses = vislib.adps_get_values(adps,ADPMetadata.Keys.LWAV_NRMSE)
    idx = np.argmin(rmses)
    adp = adps[idx]
    adp_unsc = vislib.get_unscaled_adp(dev,adp)
    calib_obj_name = adp.metadata.get(adplib.ADPMetadata.Keys.RUNTIME_CALIB_OBJ)
    calib_obj = llenums.CalibrateObjective(calib_obj_name)

    print("------ Unscaled Circuit -----")
    for cfg in adp_unsc.configs:
        block = dev.get_block(cfg.inst.block)
        for output in block.outputs:
            cfg.modes = [cfg.modes[0]]
            mdl = get_model(cfg,output)
            if mdl is None:
                continue

            print("%s mode=%s port=%s" % (cfg.inst,cfg.mode,output.name))
            print("  %s" % mdl)

    print("===== DELTA MODEL SUMMARY ====")
    print("------ Scaled Circuit / calibration objective %s -----" % calib_obj_name)
    for cfg in adp.configs:
        block = dev.get_block(cfg.inst.block)
        for output in block.outputs:
            mdl = get_model(cfg,output)
            if mdl is None:
                continue

            print("%s mode=%s port=%s" % (cfg.inst,cfg.mode,output.name))
            print("  %s" % mdl)


def scaled_circuit_block_mode_change_summary(dev,all_adps):
    adps = get_valid_adps(all_adps)
    rmses = vislib.adps_get_values(adps,ADPMetadata.Keys.LWAV_NRMSE)
    idx = np.argmin(rmses)
    adp = adps[idx]

    adp_unsc = vislib.get_unscaled_adp(dev,adp)

    header = ["block","location", "unscaled mode", "scaled mode"]
    tbl = tbllib.Tabular(header, \
                         ["%s"]*(len(header)))


    for cfg in adp.configs:
        orig_modes = adp_unsc.configs.get(cfg.inst.block,cfg.inst.loc).modes
        mode = cfg.mode
        if mode in orig_modes and len(orig_modes) > 1:
            action = "select"
            continue
        elif not mode in orig_modes:
            action = "change"
        else:
            continue

        tbl.add([ \
                        "\\tx{%s}" % cfg.inst.block, \
                        "\\tx{%s}" % str(tuple(cfg.inst.loc.address)), \
                        "\\tx{%s}" % str(orig_modes),  \
                        "\\tx{%s}" % mode])

    print(tbl.render())

def scaled_circuit_block_equation_summary(dev,all_adps):
    def get_expr(adp,dsinfo,inst,port):
        block = dev.get_block(inst.block)
        mode = adp.configs.get(inst.block,inst.loc).modes[0]
        rel = block.outputs[port].relation[mode] if block.outputs.has(port) \
            else None

        if block.outputs.has(port):
            rel = lscaleprob.get_output_relation(dev,adp,inst, \
                                                 port, \
                                                 apply_scale_transform=True)
            inputs = {}
            for var in rel.vars():
                inputs[var] = dsinfo.get_expr(inst,var)
            return rel.substitute(inputs)
        else:
            rel = lscaleprob.get_input_relation(dsinfo,dev,adp,inst, \
                                                 port, \
                                                 apply_scale_transform=True)
            return  rel

    adps = get_valid_adps(all_adps)
    if not vislib.has_waveforms(adps):
        return

    rmses = vislib.adps_get_values(adps,ADPMetadata.Keys.LWAV_NRMSE)
    idx = np.argmin(rmses)
    adp = adps[idx]

    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = lscaleprob.generate_dynamical_system_info(dev,program,adp, \
                                                       apply_scale_transform=True, \
                                                       label_integrators_only=False)


    print("------------ metadata ---------------")
    print(adp.metadata)

    print("------------ equations ---------------")
    genoplib.Const.STRING_PRECISION= 4
    genoplib.Const.STRING_SIGFIGS = 3
    for var in program.variables():
        sources = adp.get_by_source(genoplib.Var(var))
        exprs = list(map(lambda src: get_expr(adp,dsinfo,src[0],src[1]), sources))
        valid_exprs = list(filter(lambda e: not set(e.vars()) == set([var])  or \
                                  e.has_op(baseoplib.OpType.INTEG), exprs))

        if len(valid_exprs) == 0:
            continue
            #raise Exception("could not identify variable expression <%s> %s / %s" % (var,exprs,sources))

        inst,port = sources[0]
        cfg = adp.configs.get(inst.block,inst.loc)
        expr = scaled_expression_simplify(valid_exprs[0])
        clauses = genoplib.break_expr_string(expr.pretty_print())

        lhs = genoplib.Mult(genoplib.Const(cfg[port].scf,latex_style="\\rscf{%s}"), \
                            genoplib.Var(var,latex_style="\\rvar{%s}"))

        print("\\rvar{%s$_{sc}$} = %s = %s" % (var,lhs.pretty_print(),"\n\t".join(clauses)))
    print("\n\n")

    print("--------- adp ---------------")
    print(adp.to_latex())
    print("\n")

    print("--------- mode changes ---------------")
    scaled_circuit_block_mode_change_summary(dev,adps)


    print("--------- delta models  ---------------")
    delta_model_summary(dev,adps)
    return []

