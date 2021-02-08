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
import itertools
import time

class ModelCalibrateLogger(runtime_meta_util.Logger):

    def __init__(self,filename):
        self.fields = ['block','loc','mode','operation','iteration','runtime']
        runtime_meta_util.Logger.__init__(self,filename,self.fields)

    def log(self,operation,runtime):
        values = {'block':self.block.name, \
                  'loc':str(self.loc),\
                  'mode':str(self.mode), \
                  'iteration': self.iteration}

        values['operation'] = operation
        values['runtime'] = runtime
        runtime_meta_util.Logger.log(self,**values)


    def set_configured_block(self,block,loc,mode):
        self.block = block
        self.loc = loc
        self.mode = mode
        self.iteration = 0


    def set_iteration(self,idx):
        self.iteration = idx


class CandidateCodeHistory:

    def __init__(self):
        self.codes = []
        self.scores = []
        self.keys = []
        self._freqs = {}

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
        self._freqs[key] = 1

    def mark_use(self,codes):
        key = runtime_util.dict_to_identifier(codes)
        assert(key in self._freqs)
        self._freqs[key] += 1

    @property
    def freqs(self):
        for key in self.keys:
           yield self._freqs[key]
    
    @property
    def ranking(self):
        for idx,key in enumerate(self.keys):
           #yield -self._freqs[key]/self.scores[idx]
           yield self.scores[idx]
 
    def num_codes(self):
        return len(self.keys)

'''
compute set of possible codes
'''
def cast_codes_to_integer(blk,objfun,codes):
    code_names = list(codes.keys())
    possible_values = []
    best_codes = None
    best_score = None
    for code in code_names:
      lower_value = blk.state[code] \
            .nearest_value(math.floor(codes[code]))
      upper_value = blk.state[code] \
            .nearest_value(math.ceil(codes[code]))
      options = list(set([lower_value,upper_value]))
      possible_values.append(options)

    for combo in itertools.product(*possible_values):
      curr_codes = dict(zip(code_names,combo))
      minval = objfun.evaluate(curr_codes)
      if best_score is None or minval < best_score:
         best_codes = curr_codes
         best_score = minval

    return best_score,best_codes


def generate_candidate_codes(logger, \
                             code_hist, \
                             blk,calib_expr,phys_model, \
                             num_samples=3, \
                             num_offsets=1000):
    sample_ampl = 0.20
    phys_model.uncertainty.summarize()
    temp_code_hist = code_hist.copy()

    new_code_hist = CandidateCodeHistory()
    print("----- Calibration Objective -----")
    print(calib_expr)
    print("----- Generating Samples -----")
    start_time = time.time()
    for offsets in phys_model.uncertainty.samples(num_offsets, \
                                                  ampl=sample_ampl, \
                                                  include_zero=True):
        variables = dict(map(lambda tup: (tup[0],tup[1].copy().concretize()), \
                                phys_model.variables().items()))
        for v in variables.keys():
            variables[v].update_expr(lambda e: genoplib.Add(e, \
                                                            genoplib.Const(offsets[v])))

        nodes = dectree_eval.eval_expr(calib_expr, variables)
        objfun_dectree = dectreelib.RegressionNodeCollection(nodes)
        minval,codes = objfun_dectree.find_minimum()
        int_minval, int_codes = cast_codes_to_integer(blk,objfun_dectree,codes)
        if temp_code_hist.has_code(int_codes):
            #print("already exists: %s score=%f, skipping.." % (int_codes, int_minval))
            if new_code_hist.has_code(int_codes):
               new_code_hist.mark_use(int_codes) 
            continue

        #print("%s (score=%f) -> %s (score=%f)" % (codes,minval,int_codes,int_minval))
        temp_code_hist.add_code(int_codes,int_minval)
        new_code_hist.add_code(int_codes,int_minval)

    end_time = time.time()
    logger.log('gen_cand',end_time-start_time)

    best_to_worst = np.argsort(list(new_code_hist.ranking))
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
    print("expr: %s" % calib_expr)
    print("pars: %s" % pars)
    print("score: %s" % calib_score)
    input("<wait for input>")
    return calib_expr,calib_score



def codes_to_delta_model(blk,loc,out,cfg,codes):
    new_cfg = cfg.copy()
    for var,value in codes.items():
        int_value = blk.state[var].nearest_value(value)
        new_cfg[var].value = int_value


    exp_model = exp_delta_model_lib.ExpDeltaModel(blk,loc,out,new_cfg, \
                                                  calib_obj=llenums.CalibrateObjective.MODELBASED)
    return exp_model


def evaluate_candidate_codes(char_board,blk,loc,cfg,num_samples):
    models = list(exp_delta_model_lib.get_all(char_board))
    if num_samples is None:
        num_samples = len(models)
    else:
        num_samples = len(blk.outputs)*num_samples

    for mdl in models[-num_samples:]:
        calib_obj,score = evaluate_delta_model(mdl)
        yield mdl,score



def get_candidate_codes(logger,char_board,code_history,blk,loc,cfg,num_samples):

    phys_model = exp_phys_model_lib.load(char_board, \
                                         blk, \
                                         cfg=cfg)
    calib_obj = phys_model.calib_obj()
    for codes in generate_candidate_codes(logger,code_history, \
                                          blk, \
                                          calib_obj, \
                                          phys_model,  \
                                          num_samples, \
                                          num_offsets=num_samples*10):
        for out in blk.outputs:
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

def update_model(logger,char_board,blk,loc,cfg,num_model_points=3):
    #"python3 grendel.py mkphys --model-number {model} --max-depth 0 --num-leaves 1 --shrink" 
    CMDS = [ \
             "python3 grendel.py mkdeltas --model-number {model} --force > deltas.log",
             "python3 grendel.py mkphys --model-number {model} "+ \
             " --num-points {num_model_points} > phys.log"]


    adp_file = runtime_meta_util.generate_adp(char_board,blk,loc,cfg)

    runtime_sec = 0
    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=char_board.model_number, \
                         num_model_points=num_model_points)
        print(">> %s" % cmd)
        runtime_sec += runtime_meta_util.run_command(cmd)

    logger.log('upd_mdl',runtime_sec)

    runtime_meta_util.remove_file(adp_file)

# bootstrap block to get data
def bootstrap_block(logger,board,blk,loc,cfg,grid_size=9,num_samples=5):
    CMDS = [ \
             "python3 grendel.py characterize {adp} --model-number {model} --grid-size {grid_size} --num-hidden-codes {num_samples} --adp-locs > characterize.log" \
            ]


    adp_file = runtime_meta_util.generate_adp(board,blk,loc,cfg)

    runtime_sec = 0
    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=board.model_number, \
                         grid_size=grid_size, \
                         num_samples=num_samples)
        print(">> %s" % cmd)
        runtime_sec += runtime_meta_util.run_command(cmd)

    logger.log('bootstrap',runtime_sec)

    runtime_meta_util.remove_file(adp_file)

def profile_block(logger,board,blk,loc,cfg,grid_size=9):
    CMDS = [ \
             "python3 grendel.py prof {adp} --model-number {model} --grid-size {grid_size} model > profile.log" \
            ]

    adp_file = runtime_meta_util.generate_adp(board,blk,loc,cfg)

    runtime_sec = 0
    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=board.model_number, \
                         grid_size=grid_size)
        print(">> %s" % cmd)
        runtime_sec += runtime_meta_util.run_command(cmd)

    logger.log('profile',runtime_sec)

    runtime_meta_util.remove_file(adp_file)


def is_block_calibrated(board,block,loc,config, \
                        random_samples, \
                        num_iters):
    models = exp_delta_model_lib.get_models_by_calibration_objective(board, \
                                                                     llenums.CalibrateObjective.MODELBASED)
    n_models = len(models)
    if n_models >= random_samples*num_iters:
        return True
    return False




####
# Block calibration routine
#
###
def calibrate_block(logger, \
                    board,block,loc,config, \
                    grid_size=9, \
                    bootstrap_samples=5, \
                    random_samples=3, \
                    num_iters=3, \
                    cutoff=None):
    def update(num_points):
        update_model(logger,char_board,block,loc,config, \
                     num_model_points=num_points)

    logger.set_configured_block(block,loc,config.mode)

    char_model = runtime_meta_util.get_model(board,block,loc,config)
    char_board = runtime_util.get_device(char_model,layout=False)
    code_history = load_code_history_from_database(char_board)
 
    if cutoff is None:
        cutoff = 0.0
    
    if len(code_history.scores) > 0 and min(code_history.scores) <= cutoff:
        print("found code which meets cutoff=%f" % cutoff)
        return
    
    num_points = 0
    bootstrap_block(logger, \
                    char_board,block,loc,config, \
                    num_samples=bootstrap_samples, \
                    grid_size=grid_size)
    num_points += bootstrap_samples
    update(num_points)

    for iter_no in range(num_iters):
        if is_block_calibrated(char_board,block,loc,config, \
                               random_samples=random_samples, \
                               num_iters=num_iters):
            return

        print("---- iteration %d (cutoff=%f) ----" % (iter_no,cutoff))
        logger.set_iteration(iter_no)
        #input("press any key to continue...")
        n_new_codes = 0
        for exp_model in get_candidate_codes(logger, \
                                             char_board, \
                                             code_history, \
                                             block,loc,config, \
                                             num_samples=random_samples):
            exp_delta_model_lib.update(char_board,exp_model)
            n_new_codes += 1

        if n_new_codes == 0:
           print("[info] no new candidate codes were found. Returning....")
           return

        profile_block(logger, \
                      char_board,block,loc,config, \
                      grid_size=grid_size)
        num_points += random_samples
        update(num_points)

        # summarize how the recently tried codes behaved
        scores = []
        for model,score in evaluate_candidate_codes(char_board, \
                                                    block, \
                                                    loc, config, \
                                                    num_samples=random_samples*2):

            print(model)
            print(model.hidden_cfg)
            if score is None:
                print("score=<none>")
            else:
                print("score=%f" % (score))
                scores.append(score)

            print("")

        if len(scores) > 0 and min(scores) < cutoff:
            print("[info] returning early! Found code that meets cutoff=%f." % cutoff)
            return



def calibrate(args):
    board = runtime_util.get_device(args.model_number)

    logger = ModelCalibrateLogger('mdlcal_%s.log' % args.model_number)

    if not args.adp is None:
        adp = runtime_util.get_adp(board,args.adp,widen=args.widen)
        for cfg in adp.configs:
            blk = board.get_block(cfg.inst.block)
            if not blk.requires_calibration():
                continue

            cfg_modes = cfg.modes
            for mode in cfg_modes:
                cfg.modes = [mode]

                cutoff = args.cutoff
                if args.default_cutoff:
                    cutoff = runtime_meta_util.get_tolerance(blk,cfg)

                calibrate_block(logger, \
                                board,blk,cfg.inst.loc,cfg, \
                                bootstrap_samples=args.bootstrap_samples, \
                                random_samples=args.candidate_samples, \
                                grid_size=args.grid_size, \
                                num_iters=args.num_iters, \
                                cutoff=cutoff)

    else:
        for dbname in runtime_meta_util.get_block_databases(args.model_number):
            char_board = runtime_util.get_device(dbname,layout=False)
            if runtime_meta_util.database_is_empty(char_board):
                continue

            blk,loc,out,cfg = runtime_meta_util.homogenous_database_get_block_info(char_board)

            cutoff = args.cutoff
            if args.default_cutoff:
                cutoff = runtime_meta_util.get_tolerance(blk,cfg)


            calibrate_block(logger, \
                            board,blk,cfg.inst.loc,cfg, \
                            bootstrap_samples=args.bootstrap_samples, \
                            random_samples=args.candidate_samples, \
                            grid_size=args.grid_size, \
                            num_iters=args.num_iters, \
                            cutoff=cutoff)
