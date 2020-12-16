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
import random

def generate_candidate_codes(blk,calib_expr,phys_model,num_samples=3, \
                             num_offsets=1000):

    uncerts = dict(map(lambda var: (var,phys_model.uncertainty(var)), \
                       phys_model.variables().keys()))
    all_cand_codes = []
    all_cand_keys = []
    for idx in range(num_offsets):
        offsets = dict(map(lambda tup: (tup[0],random.uniform(-tup[1],tup[1])), \
                           uncerts.items()))
        variables = dict(map(lambda tup: (tup[0],tup[1].copy()), \
                                phys_model.variables().items()))
        for v in variables.keys():
            variables[v].update_expr(lambda e: genoplib.Add(e, \
                                                            genoplib.Const(offsets[v])))

        nodes = dectree_eval.eval_expr(calib_expr, variables)
        objfun_dectree = dectreelib.RegressionNodeCollection(nodes)
        minval,codes = objfun_dectree.find_minimum()
        for code_name,value in codes.items():
            int_value = blk.state[code_name].nearest_value(value)
            codes[code_name] = int_value

        key = runtime_util.dict_to_identifier(codes)
        if not key in all_cand_keys:
            all_cand_keys.append(key)
            all_cand_codes.append(codes)
            if len(all_cand_codes) >= num_samples*3:
                break

    random.shuffle(all_cand_codes)
    for idx in range(min(len(all_cand_codes),num_samples)):
        print("%d] %s" % (idx,all_cand_codes[idx]),flush=True)
        yield all_cand_codes[idx]


def codes_to_delta_model(blk,loc,out,cfg,codes):
    new_cfg = cfg.copy()
    for var,value in codes.items():
        int_value = blk.state[var].nearest_value(value)
        new_cfg[var].value = int_value


    exp_model = exp_delta_model_lib.ExpDeltaModel(blk,loc,out,new_cfg, \
                                                  calib_obj=llenums.CalibrateObjective.LINMODEL)
    return exp_model


def get_candidate_codes(char_board,blk,loc,cfg,num_samples):

    for out in blk.outputs:
        calib_obj = out.deltas[cfg.mode].objective
        # get physical model
        phys_model = exp_phys_model_lib.load(char_board, \
                                             blk, \
                                             cfg=cfg)
        assert(not phys_model is None)

        for codes in  generate_candidate_codes(blk,calib_obj,phys_model,  \
                                               num_samples, \
                                               num_offsets=1000):
            yield codes_to_delta_model(blk,loc,out,cfg,codes)


def update_model(char_board,blk,loc,cfg):
    CMDS = [ \
             "python3 grendel.py mkdeltas --model-number {model}",
             "python3 grendel.py mkphys --model-number {model} --max-depth 0 --num-leaves 1 --shrink"]


    adp_file = runtime_meta_util.generate_adp(char_board,blk,loc,cfg)

    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=char_board.model_number)
        print(">> %s" % cmd)
        runtime_meta_util.run_command(cmd)

    runtime_meta_util.remove_file(adp_file)

# bootstrap block to get data
def bootstrap_block(board,blk,loc,cfg,grid_size=9,num_samples=5):
    CMDS = [ \
             "python3 grendel.py characterize {adp} --model-number {model} --grid-size {grid_size} --num-hidden-codes 8 --adp-locs" \
            ]


    adp_file = runtime_meta_util.generate_adp(board,blk,loc,cfg)

    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=board.model_number, \
                         grid_size=grid_size)
        print(">> %s" % cmd)
        runtime_meta_util.run_command(cmd)

    runtime_meta_util.remove_file(adp_file)

def profile_block(board,blk,loc,cfg,grid_size=9):
    CMDS = [ \
             "python3 grendel.py prof {adp} --model-number {model} --grid-size {grid_size} linmodel > prof.log" \
            ]

    adp_file = runtime_meta_util.generate_adp(board,blk,loc,cfg)

    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=board.model_number, \
                         grid_size=grid_size)
        print(">> %s" % cmd)
        runtime_meta_util.run_command(cmd)

    runtime_meta_util.remove_file(adp_file)

def is_block_calibrated(board,block,loc,config, \
                        random_samples, \
                        num_iters):
    models = exp_delta_model_lib.get_models_by_calibration_objective(board, \
                                                                     llenums.CalibrateObjective.LINMODEL)
    n_models = len(models)
    if n_models >= random_samples*num_iters:
        return True
    return False

def calibrate_block(board,block,loc,config, \
                    grid_size=9, \
                    bootstrap_samples=5, \
                    random_samples=3, \
                    num_iters=3):
    char_model = runtime_meta_util.get_model(board,block,loc,config)
    char_board = runtime_util.get_device(char_model,layout=False)

    print(char_model)
    bootstrap_block(char_board,block,loc,config, \
                    num_samples=bootstrap_samples, \
                    grid_size=grid_size)
    #input("bootstrap completed. press any key to continue...")
    for iter_no in range(num_iters):
        if is_block_calibrated(char_board,block,loc,config, \
                               random_samples=random_samples, \
                               num_iters=num_iters):
            return

        print("---- iteration %d ----" % iter_no)
        update_model(char_board,block,loc,config)
        #input("press any key to continue...")
        for exp_model in get_candidate_codes(char_board, \
                                             block,loc,config, \
                                             num_samples=random_samples):
            exp_delta_model_lib.update(char_board,exp_model)
            continue

        profile_block(char_board,block,loc,config, \
                      grid_size=grid_size)


def calibrate(args):
    board = runtime_util.get_device(args.model_number)

    if not args.adp is None:
        adp = runtime_util.get_adp(board,args.adp,widen=args.widen)
        for cfg in adp.configs:
            blk = board.get_block(cfg.inst.block)
            cfg_modes = cfg.modes
            for mode in cfg_modes:
                cfg.modes = [mode]
                calibrate_block(board,blk,cfg.inst.loc,cfg, \
                                bootstrap_samples=args.bootstrap_samples, \
                                random_samples=args.candidate_samples, \
                                grid_size=args.grid_size, \
                                num_iters=args.num_iters)

    else:
        for dbname in runtime_meta_util.get_block_databases(args.model_number):
            char_board = runtime_util.get_device(dbname,layout=False)
            if runtime_meta_util.database_is_empty(char_board):
                continue

            blk,loc,out,cfg = runtime_meta_util.homogenous_database_get_block_info(char_board)
            calibrate_block(board,blk,cfg.inst.loc,cfg, \
                            bootstrap_samples=args.bootstrap_samples, \
                            random_samples=args.candidate_samples, \
                            grid_size=args.grid_size, \
                            num_iters=args.num_iters)
