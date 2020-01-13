import gpkit
import itertools

import hwlib.model as hwmodel
from hwlib.config import Labels
from hwlib.adp import AnalogDeviceProg
import hwlib.model as modelib
import hwlib.block as blocklib
import hwlib.props as props

import math
import compiler.lscale_pass.scenv as scenvlib
import compiler.lscale_pass.scenv_gpkit as scenvlib_gpkit
import compiler.lscale_pass.scenv_smt as scenvlib_smt
import compiler.lscale_pass.objective.basic_obj as basicobj
import compiler.lscale_pass.expr_visitor as exprvisitor
from compiler.lscale_pass.objective.obj_mgr import LScaleObjectiveFunctionManager

import compiler.lscale_pass.lscale_util as lscale_util
import compiler.lscale_pass.lscale_common as lscale_common

import ops.scop as scop
import ops.op as ops
import ops.interval as interval


import random
import time
import numpy as np
import util.util as util
import util.config as CONFIG
from tqdm import tqdm

def sc_get_scm_var(scenv,block_name,loc,v):
    if v.type == cont.CSMVar.Type.OPVAR:
        jvar = scenv.get_op_range_var(block_name,loc,v.port,v.handle)
    elif v.type == cont.CSMVar.Type.COEFFVAR:
        jvar = scenv.get_gain_var(block_name,loc,v.port,v.handle)
    else:
        raise Exception("unknown var type")
    return jvar


class ScaleModelExprVisitor(exprvisitor.ExprVisitor):

    def __init__(self,scenv,circ,block,loc):
        exprvisitor.ExprVisitor.__init__(self,scenv,circ,block,loc,None)

    def visit_var(self,expr):
        block,loc = self.block,self.loc
        config = self.circ.config(block.name,loc)
        scale_model = block.scale_model(config.comp_mode)
        var= scale_model.var(expr.name)
        lscale_var = sc_get_scm_var(self.scenv,block.name,loc,var)
        return scop.SCVar(lscale_var)

    def visit_pow(self,expr):
        expr1 = self.visit_expr(expr.arg1)
        expr2 = self.visit_expr(expr.arg2)
        return jop.expo(expr1,expr2.value)


    def visit_const(self,expr):
        return scop.SCConst(expr.value)

    def visit_mult(self,expr):
        expr1 = self.visit_expr(expr.arg1)
        expr2 = self.visit_expr(expr.arg2)
        return scop.SCMult(expr1,expr2)

class SCFInferExprVisitor(exprvisitor.SCFPropExprVisitor):

    def __init__(self,scenv,circ,block,loc,port):
        exprvisitor.SCFPropExprVisitor.__init__(self,\
                                                scenv,circ, \
                                                block,loc,port)

    def coeff(self,handle):
      block,loc = self.block,self.loc
      config = self.circ.config(block.name,loc)
      model = block.scale_model(config.comp_mode)
      scale_mode = model.baseline
      coeff_const = block.coeff(config.comp_mode, \
                                scale_mode,self.port)
      coeff_var = self.scenv.get_coeff_var(self.block.name, \
                                          self.loc, \
                                          self.port,handle=handle)
      return scop.SCMult(scop.SCConst(coeff_const), \
                       scop.SCVar(coeff_var))

def sc_acceptable_model(model):
    if model is None:
        return True

    return model.enabled

def sc_physics_model(scenv,scale_mode,circ,block_name,loc,port,handle):
        block = circ.board.block(block_name)
        config = circ.config(block.name,loc)

        baseline = block.baseline(config.comp_mode)
        config.set_scale_mode(scale_mode)

        modevar = scenv.decl_mode_var(block_name,loc,scale_mode)
        jvar_gain = scenv.decl_gain_var(block_name, \
                                       loc, \
                                       port,handle)
        jvar_ops = scenv.decl_op_range_var(block_name, \
                                          loc, \
                                          port,handle)

        gain = block.coeff(config.comp_mode,scale_mode,port,handle)

        props_sc = block.props(config.comp_mode,scale_mode,port,handle)
        props_bl = block.props(config.comp_mode,baseline,port,handle)
        scf = props_sc.interval().bound/props_bl.interval().bound

        jvar_phys_gain = scenv.decl_phys_gain_var(block_name, \
                                                loc, \
                                                port,handle)
        jvar_phys_ops_lower = scenv.decl_phys_op_range_scvar(block_name, \
                                                            loc, \
                                                            port,handle,
                                                            lower=True)
        jvar_phys_ops_upper = scenv.decl_phys_op_range_scvar(block_name, \
                                                            loc, \
                                                            port,handle,
                                                            lower=False)

        jvar_unc = scenv.decl_phys_uncertainty(block_name, \
                                         loc, \
                                         port,handle)

        #config.scale_mode = config.scale_mode
        model = scenv.params.model
        pars = lscale_common.get_physics_params(scenv, \
                                               circ, \
                                               block, \
                                               loc, \
                                               port, \
                                               handle=handle)
        scenv.implies(modevar,jvar_ops, scf)
        scenv.implies(modevar,jvar_gain, gain)
        scenv.implies(modevar,jvar_phys_gain, pars['gain'])
        scenv.implies(modevar,jvar_phys_ops_lower, pars['oprange_lower'])
        scenv.implies(modevar,jvar_phys_ops_upper, pars['oprange_upper'])
        scenv.implies(modevar,jvar_unc, pars['uncertainty'])
        config.set_scale_mode(baseline)
        return sc_acceptable_model(pars['model'])

def sc_coalesce_connections(circ):
    backward_links = {}
    source_links = []
    dest_links = []
    conns = []

    def get_ancestors(blk,loc,port,visited=[]):
        if not (blk,loc,port) in backward_links or \
           (blk,loc,port) in visited:
            return []
        else:
            visited = visited +[(blk,loc,port)]
            lst = children = backward_links[(blk,loc,port)]
            for sb,sl,sp in children:
                for db,dl,dp in get_ancestors(sb,sl,sp, \
                                              visited=visited):
                    if not (db,dl,dp) in lst:
                        lst.append((db,dl,dp))

            return lst


    for blkname,loc,_ in circ.instances():
        blk = circ.board.block(blkname)
        if blk.type == blocklib.BlockType.BUS:
            assert(len(blk.inputs) == 1)
            assert(len(blk.outputs) == 1)
            backward_links[(blkname,loc,blk.outputs[0])] \
                = [(blkname,loc,blk.inputs[0])]

    for sblkname,sloc,sport, \
        dblkname,dloc,dport in circ.conns():
        sblk = circ.board.block(sblkname)
        dblk = circ.board.block(dblkname)

        if not (dblkname,dloc,dport) in backward_links:
            backward_links[(dblkname,dloc,dport)] = []


        backward_links[(dblkname,dloc,dport)] = list(set( \
                                                     backward_links[(dblkname,dloc,dport)] +
                                                     [(sblkname,sloc,sport)] + \
                                                     get_ancestors(sblkname,sloc,sport) \
    ))

        # mark this block as a source
        if sblk.type != blocklib.BlockType.BUS:
            source_links.append((sblkname,sloc,sport))

        if dblk.type != blocklib.BlockType.BUS:
            dest_links.append((dblkname,dloc,dport))

        #print(sblkname,sloc,sport)
        #print(dblkname,dloc,dport)
        #for (db,dl,dp),data  in backward_links.items():
        #    print(" %s[%s].%s : %s" % (db,dl,dp,data))

    #print("=== iterate until steady state ===")
    is_steady_state = False
    while not is_steady_state:
        is_steady_state = True
        for db,dl,dp in backward_links:
            n = len(backward_links[(db,dl,dp)])
            new_links = get_ancestors(db,dl,dp)
            backward_links[(db,dl,dp)] = new_links
            m = len(backward_links[(db,dl,dp)])
            assert(m >= n)
            is_steady_state &= (n == m)
        #print("iterate")

    for dblk,dloc,dport in dest_links:
        for sblk,sloc,sport in backward_links[(dblk,dloc,dport)]:
            if not (sblk,sloc,sport) in source_links:
                continue

            yield sblk,sloc,sport, \
                dblk,dloc,dport

def sc_build_connection_constraints(scenv,circ):
    def get_range(blkname,loc,port):
        block = circ.board.block(blkname)
        config = circ.config(blkname,loc)
        baseline = block.baseline(config.comp_mode)
        props_bl = block.props(config.comp_mode, \
                               baseline, \
                               port, \
                               None)
        amt = props_bl.interval().bound
        return amt

    for sblk,sloc,sport, \
        dblk,dloc,dport in sc_coalesce_connections(circ):
        if scenv.has_op_range_var(sblk,sloc,sport) and \
           scenv.has_op_range_var(dblk,dloc,dport):
            src_ov = scenv.get_op_range_var(sblk, \
                                           sloc, \
                                           sport)
            src_max = get_range(sblk,sloc,sport)
            dest_ov = scenv.get_op_range_var(dblk, \
                                            dloc, \
                                            dport)
            dest_max = get_range(dblk,dloc,dport)
            if dblk == "integrator":
                scenv.lte( \
                         scop.SCMult(scop.SCVar(src_ov),scop.SCConst(src_max)), \
                     scop.SCMult(scop.SCVar(dest_ov),scop.SCConst(dest_max)), \
                     'jc-match-scale-modes')
            else:
                scenv.eq( \
                     scop.SCMult(scop.SCVar(src_ov),scop.SCConst(src_max)), \
                     scop.SCMult(scop.SCVar(dest_ov),scop.SCConst(dest_max)), \
                     'jc-match-scale-modes')



    return True

def sc_decl_scale_model_variables(scenv,circ):
    success = True
    for block_name,loc,config in circ.instances():
        block = circ.board.block(block_name)

        valid_scms = []
        missing_scms = []
        for scm in block.scale_modes(config.comp_mode):
            if not block.whitelist(config.comp_mode, scm):
                continue
            is_valid = True
            for port in block.inputs + block.outputs:
                for handle in list(block.handles(config.comp_mode,port)) + [None]:
                    if  not scenv.model_db.has(block.name,loc,port, \
                                               config.comp_mode, \
                                               scm,handle):
                        missing_scms.append(scm)

                        if scenv.params.only_scale_modes_with_models:
                            print("scale mode dne: %s %s[%s].%s cm=%s scm=%s handle=%s" \
                                  % (scenv.params.calib_obj,
                                     block_name,loc, \
                                     port,
                                     config.comp_mode,
                                     scm, handle))
                            is_valid = False
                            continue

                    is_valid &= sc_physics_model(scenv,scm,circ,block_name, \
                                                loc,port,handle=handle)
            if is_valid:
                valid_scms.append(scm)
        modevars = []
        for scm in missing_scms:
                scenv.model_db.log_missing_model(block.name, \
                                                  loc, \
                                                  block.outputs[0], \
                                                  config.comp_mode, \
                                                  scm)

        if len(valid_scms) == 0:
            print("no valid scale modes: %s[%s]" % (block_name,loc))
            success =False

        for scale_mode in block.scale_modes(config.comp_mode):
            if not scale_mode in valid_scms:
                continue
            modevar = scenv.get_mode_var(block_name,loc,scale_mode)
            modevars.append(modevar)

        scenv.exactly_one(modevars)

    # figure out which ports have linked scaling modes by collapsing * ports.
    sc_build_connection_constraints(scenv,circ)

    return success

def sc_build_lscale_env(prog,circ, \
                        model, \
                        mdpe, \
                        mape, \
                        vmape, \
                        mc, \
                        ignore_models=[],
                        max_freq_khz=None):
    scenv = scenvlib.LScaleInferEnv(model, \
                                    max_freq_khz=max_freq_khz, \
                                    mdpe=mape, \
                                    mape=mape, \
                                    vmape=vmape, \
                                    mc=mc)
    if not ignore_models is None:
        for block in ignore_models:
            scenv.model_db.add_ignore(block)

    # declare scaling factors
    lscale_common.decl_scale_variables(scenv,circ)
    # build continuous model constraints
    success = sc_decl_scale_model_variables(scenv,circ)
    if not success:
        scenv.fail("missing models")
        return scenv

    sc_generate_problem(scenv,prog,circ)

    for block_name,loc,config in circ.instances():
        block = circ.board.block(block_name)
        for port in block.outputs + block.inputs:
            v = scenv.get_scvar(block_name,loc,port)
            scenv.lt(scop.SCConst(1e-12), scop.SCVar(v), \
                    "ensure nonzero");
            scenv.gt(scop.SCConst(1e12), scop.SCVar(v), \
                    "ensure nonzero");

    return scenv

# traverse dynamics, also including coefficient variable
def sc_traverse_dynamics(scenv,circ,block,loc,out):
    visitor = exprvisitor.SCFPropExprVisitor(scenv,circ,block,loc,out)
    visitor.visit()

def sc_interval_constraint(scenv,circ,prob,block,loc,port,handle=None):
    lscale_util.log_info("%s[%s].%s" % (block.name,loc,port))
    config = circ.config(block.name,loc)
    baseline = block.baseline(config.comp_mode)
    prop = block.props(config.comp_mode,baseline,port,handle=handle)
    if isinstance(prop, props.AnalogProperties):
        lscale_common.analog_op_range_constraint(scenv,circ,block,loc,port,handle,
                                                '%s-%s-%s' % \
                                                (block.name,loc,port))
        lscale_common.analog_bandwidth_constraint(scenv,circ,block,loc,port,handle,
                                                 '%s-%s-%s' % \
                                                 (block.name,loc,port))

    elif isinstance(prop, props.DigitalProperties):
        lscale_common.digital_op_range_constraint(scenv,circ,block,loc,port,handle,
                                                '%s-%s-%s' % \
                                                 (block.name,loc,port))
        lscale_common.digital_quantize_constraint(scenv,circ,block,loc,port,handle,
                                                 'quantize')
        lscale_common.digital_bandwidth_constraint(scenv,prob,circ, \
                                                  block,loc,port,handle,
                                                  '%s-%s-%s' % \
                                                  (block.name,loc,port))
    else:
        raise Exception("unknown")

def sc_port_used(scenv,block_name,loc,port,handle=None):
    return scenv.in_use((block_name,loc,port,handle), \
                       tag=scenvlib.LScaleVarType.SCALE_VAR)

def sc_generate_problem(scenv,prob,circ):
    for block_name,loc,config in circ.instances():
        block = circ.board.block(block_name)
        for out in block.outputs:
            # ensure we can propagate the dynamics
            #if block.name == 'integrator':
                #scenv.interactive()

            sc_traverse_dynamics(scenv,circ,block,loc,out)

        for port in block.outputs + block.inputs:
            if sc_port_used(scenv,block_name,loc,port):
                sc_interval_constraint(scenv,circ,prob,block,loc,port)

            for handle in block.handles(config.comp_mode,port):
                if sc_port_used(scenv,block_name,loc,port,handle=handle):
                    sc_interval_constraint(scenv,circ,prob,block,loc,port, \
                                           handle=handle)



    tmin,tmax = prob.time_constant()
    if not tmax is None:
        scenv.lte(scop.SCVar(scenv.tau()), scop.SCConst(tmax),'tau-max')

    if not tmin is None:
        scenv.gte(scop.SCVar(scenv.tau()), scop.SCConst(tmin),'tau-min')

    if not scenv.uses_tau():
        input("continue")
        scenv.eq(scop.SCVar(scenv.tau()), scop.SCConst(1.0),'tau-fixed')
        pass
    else:
        scenv.lte(scop.SCVar(scenv.tau()), scop.SCConst(1e10),'tau-min')
        scenv.gte(scop.SCVar(scenv.tau()), scop.SCConst(1e-10),'tau-max')
        lscale_common.max_sim_time_constraint(scenv,prob,circ)


def apply_scale_modes(scenv,new_circ,result):
    for block_name,loc,config in new_circ.instances():
        block = new_circ.board.block(block_name)
        scale_mode = None
        for scm in block.scale_modes(config.comp_mode):
            if not scenv.has_mode_var(block_name,loc,scm):
                continue

            mode = scenv.get_mode_var(block_name,loc,scm)
            if result[mode]:
                assert(scale_mode is None)
                scale_mode = scm

        assert(not scale_mode is None)

        config.set_scale_mode(scale_mode)
        print("%s[%s] = %s" % (block_name,loc,scale_mode))
        lscale_util.log_info("%s[%s] = %s" % (block_name,loc,scale_mode))

def apply_scale_factors(scenv,new_circ,result):
    for variable,value in result.items():
        if variable == scenv.tau():
            new_circ.set_tau(value)
        else:
            tag,meta = scenv.get_lscale_var_info(variable)
            if(tag == scenvlib.LScaleVarType.SCALE_VAR):
                (block_name,loc,port,handle) = meta
                model = scenv.params.model
                bias = hwmodel.get_bias(scenv.model_db,new_circ,block_name,loc,port, \
                                        model,handle=handle)
                new_circ.config(block_name,loc) \
                        .set_scf(port,value,handle=handle)
                new_circ.config(block_name,loc) \
                        .set_bias(port,bias,handle=handle)

            elif(tag == scenvlib.LScaleVarType.INJECT_VAR):
                (block_name,loc,port,handle) = meta
                new_circ.config(block_name,loc) \
                    .set_inj(port,value)
            else:
                pass

def concretize_result(scenv,circ,nslns,obj_fun=None):
    if scenv.failed():
        return

    smtenv = scenvlib_smt.build_smt_prob(circ,scenv, \
                                         optimize=(not obj_fun is None))
    if obj_fun is None:
        generator = scenvlib_smt.solve_smt_prob(smtenv, \
                                                nslns=nslns)
    else:
        obj_expr = list(obj_fun.make(circ,scenv))[0].objective()
        generator = scenvlib_smt.optimize_smt_prob(smtenv, \
                                                   obj_fun=obj_expr, \
                                                   minimize=True, \
                                                   nslns=nslns)
    for result in generator:
        new_circ = circ.copy()
        apply_scale_modes(scenv,new_circ,result)
        apply_scale_factors(scenv,new_circ,result)
        yield new_circ


def infer_scale_config(prog,adp,nslns, \
                       model, \
                       mape, \
                       vmape, \
                       mdpe, \
                       mc, \
                       max_freq_khz=None,
                       ignore_models=[],
                       obj_fun=None):
    assert(isinstance(adp,AnalogDeviceProg))
    scenv = sc_build_lscale_env(prog,adp,
                                model=model, \
                                max_freq_khz=max_freq_khz, \
                                ignore_models=ignore_models,
                                mape=mape, \
                                vmape=vmape, \
                                mdpe=mdpe, \
                                mc=mc)

    count = 0
    for new_adp in concretize_result(scenv,adp,nslns, \
                                     obj_fun=obj_fun):
        yield new_adp
        count += 1

