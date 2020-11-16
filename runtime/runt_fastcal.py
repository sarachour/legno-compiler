import runtime.runtime_util as runt_util
from lab_bench.grendel_runner import GrendelRunner
from hwlib.adp import ADP,ADPMetadata
import json
import numpy as np
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd

import runtime.profile.planner as planlib
import runtime.profile.profiler as proflib

import runtime.dectree.dectree_fit as dectree_fit
import runtime.dectree.dectree_eval as dectree_eval
import runtime.dectree.dectree as dectreelib

import runtime.runtime_util as runtime_util

import ops.op as oplib
import ops.generic_op as genoplib

import compiler.lscale_pass.lscale_widening as widenlib

def get_existing_hidden_codes(board,blk,cfg):
    for expmodel in physapi.get_by_block_instance(board.physdb,board,blk,\
                                                  cfg.inst.loc, cfg,\
                                                  hidden=False):
        if not expmodel.delta_model.complete:
            fitlib.fit_delta_model(expmodel)


        if not expmodel.delta_model.complete:
            continue


        hidden_codes = dict(map(lambda st: (st.name,[]), \
                                filter(lambda st: isinstance(st.impl,blocklib.BCCalibImpl), \
                                       blk.state)))

        pars = dict(expmodel.delta_model.params)
        pars[physlib.ExpPhysModel.MODEL_ERROR] = expmodel.delta_model.model_error
        yield hidden_codes,pars

def fit_phys_model(board,blk,loc,cfg,objfun_dectree,objfun_expr):
    assert(isinstance(objfun_expr,oplib.Op))
    assert(isinstance(objfun_dectree, lindectreelib.RegressionNodeCollection))
    objfun_vals = []
    hidden_codes = dict(map(lambda st: (st.name,[]), \
                            filter(lambda st: isinstance(st.impl,blocklib.BCCalibImpl), \
                               blk.state)))

    for expmodel in physapi.get_by_block_instance(board.physdb,board,blk,\
                                                  cfg.inst.loc, cfg,\
                                                  hidden=False):
        if not expmodel.delta_model.complete:
            fitlib.fit_delta_model(expmodel)

        if not expmodel.delta_model.complete:
            continue

        for hidden_code in hidden_codes:
            hidden_codes[hidden_code].append(expmodel.cfg[hidden_code].value)

        pars = dict(expmodel.delta_model.params)
        pars[physlib.ExpPhysModel.MODEL_ERROR] = expmodel.delta_model.model_error
        value = objfun_expr.compute(pars)
        objfun_vals.append(value)

    print("num points: %d" % len(objfun_vals))
    if len(objfun_vals) > 0 and \
       objfun_dectree.fit({'inputs':hidden_codes, \
                            'meas_mean':objfun_vals}):
        assert(objfun_dectree.is_concrete())
        return True
    else:
        return False


def fast_calibrate_adp(args):
    board = runt_util.get_device(args.model_number)
    char_board = runt_util.get_device(args.char_data)
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))

    runtime = GrendelRunner()
    runtime.initialize()
    method = llenums.CalibrateObjective(args.method)
    delta_model_label = runtime_util.DeltaModelLabel \
                                .from_calibration_objective(method, \
                                                            legacy=False)
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)


        cfg_modes = cfg.modes
        for mode in widenlib.widen_modes(blk,cfg):
            cfg.modes = [mode]
            if not blk.requires_calibration():
                continue

            print("%s" % (cfg.inst))
            print(cfg)
            print('----')

            if runt_util.is_calibrated(board,blk,cfg.inst.loc, \
                             cfg,delta_model_label):
                print("-> already calibrated")
                continue

            phys_model = physapi.get_physical_model(char_board.physdb, \
                                                    board, \
                                                    blk, \
                                                    cfg=cfg)
            if phys_model is None:
                print("-> no physical model available!")
                continue

            terms = []
            objfun_expr = genoplib.product(list(map(lambda out: out.deltas[cfg.mode].objective, \
                                                blk.outputs)))
            objfun_dectree = lindectreelib.RegressionNodeCollection(lindectree_eval \
                                                                    .eval_expr(objfun_expr,  \
                                                                               phys_model.params))
            print("minimization objective: %s" % objfun_expr)

            #concrete physical model

            print('---> Counting existing samples')
            samples = []
            for hidden_codes,delta_pars in get_existing_hidden_codes(board,blk,cfg):
                samples.append(hidden_codes)
            print("  num-samples: %d" % len(samples))

            print("---> Bootstrapping model")
            new_samples = objfun_dectree.random_sample(samples)
            print("   new-samples: %d" % (len(new_samples)))
            for sample in new_samples:
                planner = planlib.SingleTargetedPointPlanner(blk,cfg.inst.loc,cfg, \
                                                             n=args.grid_size, \
                                                             m=args.grid_size, \
                                                             hidden_codes=sample)
                proflib.profile_all_hidden_states(runtime,board,planner)

            print("# samples: %s" % len(samples))
            if not fit_phys_model(board,blk,cfg.inst.loc,cfg, \
                                  objfun_dectree, \
                                  objfun_expr):
                print("-> could not fit physical model. Maybe not enough points?")
                continue

            minval, best_hidden_codes = objfun_dectree.find_minimum()
            print("---- found next prediction ----")
            print("minimum: %s" % str(minval))
            print("  hidden-codes: %s" % best_hidden_codes)
            upd_cfg = cfg.copy()
            for hidden_code,value in best_hidden_codes.items():
                upd_cfg[hidden_code].value = value

            print("-> updating code")
            for output in blk.outputs:
                print(upd_cfg)
                print("label: %s" % delta_model_label)
                exp = deltalib.ExpCfgBlock(board.physdb, \
                                           board, \
                                           blk, \
                                           cfg.inst.loc, \
                                           output, \
                                           upd_cfg, \
                                           status_type=board.profile_status_type, \
                                           method_type=board.profile_op_type)
                exp.delta_model.label = delta_model_label
                exp.update()

