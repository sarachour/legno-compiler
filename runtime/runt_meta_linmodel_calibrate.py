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

def summarize_model(char_board,blk,cfg):

    print(cfg)

    for out in blk.outputs:
        print("########")
        print("OUTPUT %s" % out.name)
        print("########")
        calib_obj = out.deltas[cfg.mode].objective
        # get physical model
        phys_model = exp_phys_model_lib.load(char_board, \
                                             blk, \
                                             cfg=cfg)

        if phys_model is None:
            print("[[warn]] this output has no physical model")
            continue

        variables = dict(map(lambda tup: (tup[0],tup[1].copy()), \
                                    phys_model.variables().items()))

        for var,dectree in variables.items():
            print("===== %s =====" % var)
            print(dectree.pretty_print())



        print("==== Calibrate Expression ====")
        print(calib_obj)
        #input()

class CandidateCodeHistory:

    def __init__(self):
        self.codes = []
        self.scores = []
        self.keys = []

    def copy(self):
        chist = CandidateCodeHistory()
        for idx in range(self.num_codes()):
            chist.add_code(self.codes[idx],self.scores[idx])
        return chist

    def has_code(self,codes):
        key = runtime_util.dict_to_identifier(codes)
        return key in self.keys

    def add_code(self,codes,score):
        key = runtime_util.dict_to_identifier(codes)
        if key in self.keys:
            raise Exception("code already tested: %s score=%f" % (codes,score))

        self.keys.append(key)
        self.codes.append(codes)
        self.scores.append(score)


    def num_codes(self):
        return len(self.keys)

def generate_candidate_codes(code_hist, \
                             blk,calib_expr,phys_model, \
                             num_samples=3, \
                             num_offsets=1000):
    sample_ampl = 0.0
    phys_model.uncertainty.summarize()
    temp_code_hist = code_hist.copy()
    new_code_hist = CandidateCodeHistory()

    print("----- Generating Samples -----")
    for offsets in phys_model.uncertainty.samples(num_offsets,ampl=sample_ampl,include_zero=True):
        variables = dict(map(lambda tup: (tup[0],tup[1].copy().concretize()), \
                                phys_model.variables().items()))
        for v in variables.keys():
            variables[v].update_expr(lambda e: genoplib.Add(e, \
                                                            genoplib.Const(offsets[v])))

        nodes = dectree_eval.eval_expr(calib_expr, variables)
        objfun_dectree = dectreelib.RegressionNodeCollection(nodes)
        _,codes = objfun_dectree.find_minimum()
        for code_name,value in codes.items():
            int_value = blk.state[code_name].nearest_value(value)
            codes[code_name] = int_value

        if temp_code_hist.has_code(codes):
            continue

        minval = objfun_dectree.evaluate(codes)
        temp_code_hist.add_code(codes,minval)
        new_code_hist.add_code(codes,minval)

    best_to_worst = np.argsort(new_code_hist.scores)
    for ident,idx in enumerate(best_to_worst[:num_samples]):
        print("%d] %s (score=%f)" % (ident, \
                                     new_code_hist.codes[idx],\
                                     new_code_hist.scores[idx]),flush=True)
        code_hist.add_code(new_code_hist.codes[idx],new_code_hist.scores[idx])
        yield new_code_hist.codes[idx]

def evaluate_delta_model(mdl,num_samples=None):
    if not num_samples is None:
        models = models[-num_samples:]

    calib_expr = mdl.output.deltas[mdl.config.mode].objective
    pars = mdl.variables()
    if not all(map(lambda v: v in pars, calib_expr.vars())):
        print("[[warn]] not all variables are part of prediction")
        print("model-vars: %s" % str(pars.keys()))
        return calib_expr,None

    calib_score = calib_expr.compute(pars)
    return calib_expr,calib_score



def codes_to_delta_model(blk,loc,out,cfg,codes):
    new_cfg = cfg.copy()
    for var,value in codes.items():
        int_value = blk.state[var].nearest_value(value)
        new_cfg[var].value = int_value


    exp_model = exp_delta_model_lib.ExpDeltaModel(blk,loc,out,new_cfg, \
                                                  calib_obj=llenums.CalibrateObjective.LINMODEL)
    return exp_model


def evaluate_candidate_codes(char_board,blk,loc,cfg,num_samples):
    models = list(exp_delta_model_lib.get_all(char_board))
    if num_samples is None:
        num_samples = len(models)

    for mdl in models[-num_samples:]:
        calib_obj,score = evaluate_delta_model(mdl)
        print(mdl)
        if score is None:
            print("score=<none>")
        else:
            print("score=%f" % (score))
        print("")


def get_candidate_codes(char_board,code_history,blk,loc,cfg,num_samples):

    for out in blk.outputs:
        calib_obj = out.deltas[cfg.mode].objective
        # get physical model
        phys_model = exp_phys_model_lib.load(char_board, \
                                             blk, \
                                             cfg=cfg)
        assert(not phys_model is None)

        for codes in  generate_candidate_codes(code_history, \
                                               blk,calib_obj,phys_model,  \
                                               num_samples, \
                                               num_offsets=num_samples*10):
            yield codes_to_delta_model(blk,loc,out,cfg,codes)

def load_code_history_from_database(char_board):
    code_hist = CandidateCodeHistory()
    models = list(exp_delta_model_lib.get_all(char_board))
    for mdl in models:
        codes = dict(mdl.hidden_codes())
        calib_obj,score = evaluate_delta_model(mdl)
        if score is None:
            score = 9999.0

        print("hist %s score=%f" % (codes,score))
        if not code_hist.has_code(codes):
           code_hist.add_code(codes,score)

    return code_hist

def update_model(char_board,blk,loc,cfg,num_model_points=3):
    #"python3 grendel.py mkphys --model-number {model} --max-depth 0 --num-leaves 1 --shrink" 
    CMDS = [ \
             "python3 grendel.py mkdeltas --model-number {model} --force > deltas.log",
             "python3 grendel.py mkphys --model-number {model} "+ \
             " --num-points {num_model_points} > phys.log"]


    adp_file = runtime_meta_util.generate_adp(char_board,blk,loc,cfg)

    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=char_board.model_number, \
                         num_model_points=num_model_points)
        print(">> %s" % cmd)
        runtime_meta_util.run_command(cmd)

    runtime_meta_util.remove_file(adp_file)

# bootstrap block to get data
def bootstrap_block(board,blk,loc,cfg,grid_size=9,num_samples=5):
    CMDS = [ \
             "python3 grendel.py characterize {adp} --model-number {model} --grid-size {grid_size} --num-hidden-codes {num_samples} --adp-locs > characterize.log" \
            ]


    adp_file = runtime_meta_util.generate_adp(board,blk,loc,cfg)

    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=board.model_number, \
                         grid_size=grid_size, \
                         num_samples=num_samples)
        print(">> %s" % cmd)
        runtime_meta_util.run_command(cmd)

    runtime_meta_util.remove_file(adp_file)

def profile_block(board,blk,loc,cfg,grid_size=9):
    CMDS = [ \
             "python3 grendel.py prof {adp} --model-number {model} --grid-size {grid_size} linmodel > profile.log" \
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
    def update(num_points):
        update_model(char_board,block,loc,config, \
                     num_model_points=num_points)

    char_model = runtime_meta_util.get_model(board,block,loc,config)
    char_board = runtime_util.get_device(char_model,layout=False)

    #summarize_model(char_board,block,config)

    num_points = 0
    bootstrap_block(char_board,block,loc,config, \
                    num_samples=bootstrap_samples, \
                    grid_size=grid_size)
    num_points += bootstrap_samples
    update(num_points)
    code_history = load_code_history_from_database(char_board)

    #input("bootstrap completed. press any key to continue...")
    for iter_no in range(num_iters):
        if is_block_calibrated(char_board,block,loc,config, \
                               random_samples=random_samples, \
                               num_iters=num_iters):
            return

        print("---- iteration %d ----" % iter_no)

        #input("press any key to continue...")
        n_new_codes = 0
        for exp_model in get_candidate_codes(char_board, \
                                             code_history, \
                                             block,loc,config, \
                                             num_samples=random_samples):
            exp_delta_model_lib.update(char_board,exp_model)
            n_new_codes += 1

        if n_new_codes == 0:
           print("[info] no new candidate codes were found. Returning....")
           return

        profile_block(char_board,block,loc,config, \
                      grid_size=grid_size)
        num_points += random_samples
        update(num_points)

        evaluate_candidate_codes(char_board, \
                                 block, \
                                 loc, config, \
                                 num_samples=random_samples*2)



def calibrate(args):
    board = runtime_util.get_device(args.model_number)

    if not args.adp is None:
        adp = runtime_util.get_adp(board,args.adp,widen=args.widen)
        for cfg in adp.configs:
            blk = board.get_block(cfg.inst.block)
            if not blk.requires_calibration():
                continue

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
