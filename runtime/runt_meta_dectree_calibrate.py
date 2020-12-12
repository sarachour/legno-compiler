import runtime.runtime_util as runtime_util
import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib
import runtime.dectree.dectree_eval as dectree_eval
import runtime.dectree.dectree as dectreelib
import runtime.dectree.region as regionlib

import hwlib.hcdc.llenums as llenums
import ops.generic_op as genoplib
import ops.opparse as parser
import numpy as np
import math

def get_good_codes(blk,calib_obj,uncertainties,phys_model,coverage=0.005):
    good_codes = []
    for var,uncert in uncertainties.items():
        region = regionlib.Region()
        for sign in [1,-1]:
            offset = uncert*sign
            print('var=%s uncert=%f' % (var,offset))
            variables = dict(map(lambda tup: (tup[0],tup[1].copy()), \
                                phys_model.variables().items()))
            variables[var].update_expr(lambda e: genoplib.Add(e, \
                                                              genoplib.Const(offset)))
            nodes = dectree_eval.eval_expr(calib_obj, variables)
            objfun_dectree = dectreelib.RegressionNodeCollection(nodes)
            minval,codes = objfun_dectree.find_minimum()
            for v,value in codes.items():
                int_value = blk.state[v].nearest_value(value)
                region.extend_range(v, int_value,int_value)

        n_codes = round(max(1,coverage*region.combinations()))
        print(region.combinations(),n_codes)
        for _ in range(n_codes):
            code = region.random_code()
            key = runtime_util.dict_to_identifier(code)
            if not key in good_codes:
                yield code
                good_codes.append(key)

def codes_to_delta_model(blk,loc,out,cfg,codes):
    new_cfg = cfg.copy()
    for var,value in codes.items():
        int_value = blk.state[var].nearest_value(value)
        new_cfg[var].value = int_value


    exp_model = exp_delta_model_lib.ExpDeltaModel(blk,loc,out,new_cfg, \
                                                  calib_obj=llenums.CalibrateObjective.NONE)
    return exp_model


def dectree_calibrate(board):
    blk,loc,out,cfg = runtime_meta_util.homogenous_database_get_block_info(board)

    if len(exp_delta_model_lib.get_all(board)) < 200:
        return None

    PHYS_CMD = "python3 grendel.py mkphys --model-number {model} --max-depth 0 --num-leaves 1 --shrink"
    cmd = PHYS_CMD.format(model=board.model_number)
    runtime_meta_util.run_command(cmd)

    calib_obj = out.deltas[cfg.mode].objective
    phys_model = exp_phys_model_lib.load(board, \
                                         blk, \
                                         cfg=cfg)
    assert(not phys_model is None)
    variables = dict(map(lambda tup: (tup[0],tup[1].copy()), \
                         phys_model.variables().items()))

    nodes = dectree_eval.eval_expr(calib_obj, variables)
    objfun_dectree = dectreelib.RegressionNodeCollection(nodes)
    minval,codes = objfun_dectree.find_minimum()
    for var,value in codes.items():
        codes[var] = blk.state[var].nearest_value(value)

    # compute uncertainty on objective function
    uncerts = dict(map(lambda var: (var,phys_model.uncertainty(var)), \
                       phys_model.variables().keys()))
    objfun_unc = calib_obj.compute(uncerts)
    for codes in get_good_codes(blk,calib_obj,uncerts,phys_model):
        yield codes_to_delta_model(blk,loc,out,cfg,codes)


def calibrate(args):
    board = runtime_util.get_device(args.model_number)
    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.BEST)
    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.DECTREE)

    for dbname in runtime_meta_util.get_block_databases(args.model_number):
        char_board = runtime_util.get_device(dbname,layout=False)
        runtime_meta_util.fit_delta_models(char_board,log_file='mkdeltas.log')
        # make sure the database only concerns one configured block
        assert(runtime_meta_util.database_is_homogenous(char_board))
        # fitting any outstanding delta models
        # get the best model from bruteforcing operation
        for model in dectree_calibrate(char_board):
            print(model)
            exp_delta_model_lib.update(char_board,model)
            print("-> profiling")
            runtime_meta_util.profile(char_board,char_board, \
                                      llenums.CalibrateObjective.NONE, \
                                      log_file='profile.log')
            print("-> fitting")
            runtime_meta_util.fit_delta_models(board)


        # update the original database to include the best brute force model
        #exp_delta_model_lib.update(board,best_model)
        # profile bruteforce model if you haven't already
        #runtime_meta_util.profile(board,char_board, \
        #                          llenums.CalibrateObjective.DECTREE)
        #runtime_meta_util.fit_delta_models(board)

