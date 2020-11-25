from lab_bench.grendel_runner import GrendelRunner
import json
import numpy as np

import hwlib.block as blocklib
from hwlib.adp import ADP,ADPMetadata

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd

import runtime.runtime_util as runt_util
import runtime.profile.planner as planlib
import runtime.profile.profiler as proflib

import runtime.dectree.dectree_fit as dectree_fit
import runtime.dectree.dectree_eval as dectree_eval
import runtime.dectree.dectree_optsample as dectree_optsample_lib
import runtime.dectree.dectree as dectreelib

import runtime.runtime_util as runtime_util

import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib

import runtime.runt_mkdeltamodels as runt_mkdeltamodels

import ops.op as oplib
import ops.generic_op as genoplib

### TODO: just fit the variables in use
### TODO: initial condition scans over x port as well. Not necessary.
class MinimizationObjective:

    def __init__(self,blk,loc,cfg,phys_model):
        self.block = blk
        self.config = cfg
        self.loc = loc
        self.phys_model = phys_model

        # concrete
        self.expr = self.make_objective_func(blk,cfg)
        self.variables = dict(map(lambda tup: (tup[0],tup[1].copy()), \
                                               self.phys_model.variables().items()))


    @staticmethod
    def make_objective_func(blk,cfg):
        objfun_expr = genoplib.product(list(map(lambda out:  \
                                                out.deltas[cfg.mode].objective, \
                                                blk.outputs)))
        return objfun_expr


    def random_sample(self,samples):
        new_samples = []
        expr_vars = self.expr.vars()
        nodes = map(lambda tup: tup[1], \
                    filter(lambda tup: tup[0] in self.expr.vars(),  \
                           self.variables.items()))
        return dectree_optsample_lib.random_sample(list(nodes),samples)

    def fit(self,dev):
        npts,hidden_codes,deltavar_vals,objfun_vals = self.get_data(dev)
        if npts > 0:
            for var in self.expr.vars():
                dectree = self.variables[var]
                dectree.fit({'inputs':hidden_codes, \
                             'meas_mean':deltavar_vals[var]})
            return True
        else:
            return False


    def minimize(self):
        nodes = dectree_eval.eval_expr(self.expr, \
                                       self.variables)

        objfun_dectree = dectreelib.RegressionNodeCollection(nodes)
        minval,codes = objfun_dectree.find_minimum()
        for var,value in codes.items():
            codes[var] = self.block.state[var].nearest_value(value)

        return minval,codes

    def get_data(self,dev):
        objfun_vals = []
        hidden_codes = dict(map(lambda st: (st.name,[]), \
                                filter(lambda st: isinstance(st.impl,blocklib.BCCalibImpl), \
                                       self.block.state)))
        expr_vars = self.expr.vars()
        deltavar_vals = dict(map(lambda var: (var,[]), expr_vars))
 
        total_pts = 0
        for delta_model in exp_delta_model_lib.get_models_by_block_instance(dev, \
                                                                            self.block,\
                                                                            self.loc, \
                                                                            self.config):
            total_pts += 1
            if not delta_model.is_concrete(expr_vars):
                continue

            for hidden_code in hidden_codes:
                hidden_codes[hidden_code].append(delta_model.config[hidden_code].value)

            for var in expr_vars:
                deltavar_vals[var].append(delta_model.get_value(var))

            value = self.expr.compute(delta_model.variables())
            objfun_vals.append(value)

        print("num points: %d/%d" % (len(objfun_vals),total_pts))
        return len(objfun_vals),hidden_codes,deltavar_vals,objfun_vals


def build_objective_function(blk,cfg,phys_model):
    terms = []
    objfun = MinimizationObjective(blk,cfg.inst.loc,cfg, \
                                   phys_model)

    print("minimization objective: %s" % objfun.expr)
    return objfun

def bootstrap_phys_model(runtime,board,blk,cfg,objfun,grid_size):
    print("---> Retrieve Existing Samples")

    samples = []
    npts,hidden_codes,_,_ = objfun.get_data(board)
    samples = []
    for idx in range(npts):
        sample = dict(map(lambda tup: (tup[0],tup[1][idx]), \
                          hidden_codes.items()))
        samples.append(sample)

    print("---> Bootstrapping model")
    print("   current-samples: %d" % len(samples))

    new_samples = objfun.random_sample(samples)
    print("   new-samples: %d" % (len(new_samples)))
    for idx,sample in enumerate(new_samples):
        for output in blk.outputs:
            for method,n,m,reps in runtime_util.get_profiling_steps(output, \
                                                               cfg, \
                                                               grid_size):
                print("=> [[sample %d/%d]] n=%d m=%d hidden_codes=%s" \
                      %(idx,len(new_samples),n,m,sample))
                planner = planlib.SingleTargetedPointPlanner(blk, \
                                                             loc=cfg.inst.loc, \
                                                             output=output, \
                                                             cfg=cfg, \
                                                             method=method, \
                                                             n=n, \
                                                             m=m, \
                                                             reps=reps, \
                                                             hidden_codes=sample)
                proflib.profile_all_hidden_states(runtime,board,planner)

    if len(new_samples) > 0:
        print("=== update delta models ===")
        runt_mkdeltamodels.update_delta_models_for_configured_block(board, \
                                                                    blk, \
                                                                    cfg.inst.loc, \
                                                                    cfg, \
                                                                    hidden=False)


def fast_calibrate_adp(args):
    board = runt_util.get_device(args.model_number)
    char_board = runt_util.get_device(args.char_data)
    adp = runtime_util.get_adp(board,args.adp)

    runtime = GrendelRunner()
    runtime.initialize()
    calib_obj = llenums.CalibrateObjective.FAST
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            if not blk.requires_calibration():
                continue

            print("%s" % (cfg.inst))
            print(cfg)
            print('----')

            if exp_delta_model_lib.is_calibrated(board,blk,cfg.inst.loc, \
                                                 cfg,calib_obj):
                print("-> already calibrated")
                continue

            phys_model = exp_phys_model_lib.load(char_board, \
                                                 blk, \
                                                 cfg=cfg)
            if phys_model is None:
                print("-> no physical model available!")
                continue

            objfun = build_objective_function(blk,cfg,phys_model)

            bootstrap_phys_model(runtime, \
                                 char_board, \
                                 blk, \
                                 cfg, \
                                 objfun, \
                                 args.grid_size)
            #concrete physical model

            print("==== fitting model ====")
            if not objfun.fit(char_board):
                print("[[error]] could not fit physical model")
                continue

            minval, best_hidden_codes = objfun.minimize()
            print("---- found next prediction ----")
            print("minimum: %s" % str(minval))
            print("  hidden-codes: %s" % best_hidden_codes)
            upd_cfg = cfg.copy()
            for hidden_code,value in best_hidden_codes.items():
                upd_cfg[hidden_code].value = value

            print("-> updating code")
            for output in blk.outputs:
                print(upd_cfg)
                delta_model = exp_delta_model_lib.ExpDeltaModel(blk, \
                                                   cfg.inst.loc, \
                                                   output, \
                                                   upd_cfg)
                delta_model.calib_obj = calib_obj
                exp_delta_model_lib.update(board,delta_model)

