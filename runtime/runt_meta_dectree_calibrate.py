import runtime.runtime_util as runtime_util
import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib
import runtime.dectree.dectree_eval as dectree_eval
import runtime.dectree.dectree as dectreelib

import hwlib.hcdc.llenums as llenums
import ops.generic_op as genoplib
import ops.opparse as parser
import numpy as np

def dectree_calibrate(board):
    blk,loc,out,cfg = runtime_meta_util.homogenous_database_get_block_info(board)

    if len(exp_delta_model_lib.get_all(board)) < 200:
        return None

    PHYS_CMD = "python3 grendel.py mkphys --model-number {model} --max-depth 3 --num-leaves 10"
    cmd = PHYS_CMD.format(model=board.model_number)
    runtime_meta_util.run_command(cmd)

    calib_obj = out.deltas[cfg.mode].objective
    calib_obj = parser.parse_expr('max(modelError,0)')
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

    print("===== best dectree (score=%f) ====" % (minval))
    print(codes)

    new_cfg = cfg.copy()
    for var,value in codes.items():
        new_cfg[var].value = value

    exp_model = exp_delta_model_lib.ExpDeltaModel(blk,loc,out,new_cfg, \
                                      calib_obj=llenums.CalibrateObjective.DECTREE)
    return exp_model

def calibrate(args):
    board = runtime_util.get_device(args.model_number)
    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.BEST)
    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.DECTREE)

    for dbname in runtime_meta_util.get_block_databases(args.model_number):
        char_board = runtime_util.get_device(dbname,layout=False)
        runtime_meta_util.fit_delta_models(char_board)
        # make sure the database only concerns one configured block
        assert(runtime_meta_util.database_is_homogenous(char_board))
        # fitting any outstanding delta models
        # get the best model from bruteforcing operation
        best_model = dectree_calibrate(char_board)
        if best_model is None:
            continue

        # update the original database to include the best brute force model
        exp_delta_model_lib.update(board,best_model)
        # profile bruteforce model if you haven't already
        runtime_meta_util.profile(board,char_board, \
                                  llenums.CalibrateObjective.DECTREE)
        runtime_meta_util.fit_delta_models(board)

