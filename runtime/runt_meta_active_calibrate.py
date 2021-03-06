import runtime.runtime_util as runtime_util
import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib
import runtime.fit.model_fit as modelfitlib

import hwlib.hcdc.llenums as llenums
import ops.generic_op as genoplib
import ops.base_op as baseoplib
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


class HiddenCodePool:

    def __init__(self,variables,predictor):
        self.variables = variables
        self.ranges = {}
        self.pool = []
        self.scores = []
        self.pool_keys = []

    def set_range(self,var,values):
        self.ranges[var] = values

    def has_code(self,codes):
        key = runtime_util.dict_to_identifier(codes)
        return key in self.pool_keys

    def add_code(self,codes,score):
        key = runtime_util.dict_to_identifier(codes)
        if key in self.pool_keys:
            raise Exception("code already tested: %s score=%f" % (codes,score))

        self.pool_keys.append(key)
        vals = list(map(lambda v: codes[v], self.variables))
        self.codes.append(vals)
        self.scores.append(score)

    @property
    def ranking(self):
        for idx,key in enumerate(self.keys):
           yield self.scores[idx]
 
    def num_codes(self):
        return len(self.keys)

class Predictor:
    class Data:

        def __init__(self,outputs,hidden_codes):
            self.outputs = outputs
            self.hidden_codes = list(map(lambda hc: hc.name, hidden_codes))
            self.dataset = {}
            for out in outputs:
                self.dataset[out] = {}

        def add_variable(self,output,var):
            self.dataset[output.name][var] = {'codes':[], 'values':[]}

        def add_datapoint(self,output,var,codes,val):
            hcs = []
            for code in self.hidden_codes:
                hcs.append(codes[code])

            self.dataset[output.name][var]['values'].append(val)
            self.dataset[output.name][var]['codes'].append(hcs)

        def get_dataset(self,output,var):
            ds = self.dataset[output.name][var]
            values = ds['values']
            codes = dict(map(lambda hc : (hc,[]), self.hidden_codes))
            for hcs in ds['codes']:
                for hc_name,value in zip(self.hidden_codes, hcs):
                    codes[hc_name].append(value)
            return codes,values


    def __init__(self,blk,loc,cfg):
        self.variables = {}
        self.objectives = {}
        self.block = blk
        self.loc = loc
        self.config= cfg
        self.data = Predictor.Data(list(map(lambda o: o.name, self.block.outputs)), \
                                   runtime_util.get_hidden_codes(self.block))


    def add_objective(self,out,expr):
        assert(isinstance(expr,baseoplib.Op))
        if not out in self.objectives:
            self.objectives[out.name] = []

        self.objectives[out.name].append(expr)

    def set_variable(self,out,v,mdl):
        assert(not (out.name,v) in self.variables)
        self.variables[(out.name,v)] = mdl
        self.data.add_variable(out,v)

    def min_samples(self):
        return max(map(lambda v: len(v.params) + 1, self.variables.values()))


    def fit(self):
        for  (out,var),model in self.variables.items():
            codes,values = self.data.get_dataset(self.block.outputs[out],var)
            if len(values) == 0:
                raise Exception("no data for fitting variable <%s> at output <%s>" % (var,out))

            modelfitlib.fit_model(model.params,model.expr,{'inputs':codes,'meas_mean':values})

 

def load_code_pool_from_database(char_board,block,predictor):
    hidden_codes = list(map(lambda st: st.name, \
                            runtime_util.get_hidden_codes(block)))
    code_pool= HiddenCodePool(hidden_codes,predictor)
    for hc in hidden_codes:
        vals  = block.state[hc].values
        code_pool.set_range(hc,vals)

    models = list(exp_delta_model_lib.get_all(char_board))
    for mdl in models:
        codes = dict(mdl.hidden_codes())
        calib_obj,score = evaluate_delta_model(mdl)
        if score is None:
            score = 9999.0

        print("hist %s score=%f" % (codes,score))
        if not code_hist.has_code(codes):
           code_pool .add_code(codes,score)

    return code_pool



def update_model(logger,char_board,blk,loc,cfg,num_model_points=3):
    #"python3 grendel.py mkphys --model-number {model} --max-depth 0 --num-leaves 1 --shrink" 
    CMDS = [ \
             "python3 grendel.py mkdeltas --model-number {model} --force > deltas.log" \
    ]


    adp_file = runtime_meta_util.generate_adp(char_board,blk,loc,cfg)

    runtime_sec = 0
    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=char_board.full_model_number, \
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
                         model=board.full_model_number, \
                         grid_size=grid_size, \
                         num_samples=num_samples)
        print(">> %s" % cmd)
        runtime_sec += runtime_meta_util.run_command(cmd)

    logger.log('bootstrap',runtime_sec)

    runtime_meta_util.remove_file(adp_file)



def build_predictor(xfer_board,block,loc,config):
    predictor = Predictor(block,loc,config)
    for output in block.outputs:
        phys_model = exp_phys_model_lib.load(xfer_board,block,config,output)
        for var,pmodel in phys_model.variables().items():
            predictor.set_variable(output,var,pmodel)

        predictor.add_objective(output, output.deltas[config.mode].objective)

    return predictor


# fit all the predictor parameters using initial number of samples.
def update_predictor(predictor,char_board):
     nsamples = predictor.min_samples()

     for model in exp_delta_model_lib.get_all(char_board):
        if nsamples == 0:
            break

        for var,val in model.variables().items():
            predictor.data.add_datapoint(model.output, var,  \
                                         dict(model.hidden_codes()), val)

        nsamples -= 1

     predictor.fit()

####
# Block calibration routine
#
###
def calibrate_block(logger, \
                    board,xfer_board, \
                    block,loc,config, \
                    grid_size=9, \
                    random_samples=3, \
                    num_iters=3, \
                    cutoff=None):
    logger.set_configured_block(block,loc,config.mode)

    # get board with initial code pool
    char_model = runtime_meta_util.get_model(board,block,loc,config)
    char_board = runtime_util.get_device("active-cal/%s" % char_model,layout=False)

    # load physical models for transfer learning. Compute the number of parameters
    phys_models = {}
    nsamps_reqd = 0


    # build a calibration objective predictor with per-variable models.
    predictor = build_predictor(xfer_board,block,loc,config)
    nsamps_reqd = predictor.min_samples()

    # collect initial data for fitting the transfer model
    # and fit all of the initial guesses for the parameters on the transfer model
    # this should give us an initial predictor
    print("==== BOOTSTRAPPING <#samps=%d> ====" % nsamps_reqd)
    '''
    bootstrap_block(logger, \
                    char_board,block,loc,config, \
                    grid_size=grid_size, \
                    num_samples=nsamps_reqd)
    update_model(logger,char_board,block,loc,config)
     '''

    print("TODO: uncomment, skipping for now")
    update_predictor(predictor,char_board)

    # next, we're going to populate the initial pool of points.
    # we're going to pick some 
    print("==== SETUP POOL ====")
    code_pool= load_code_pool_from_database(char_board,block, predictor)
    code_pool.random_points(10)
    code_pool.predict()
    print(code_pool)
    raise Exception("TODO: active learning and pptimization")

def calibrate(args):
    board = runtime_util.get_device(args.model_number)
    xfer_board = runtime_util.get_device(args.xfer_db)

    logger = ModelCalibrateLogger('actcal_%s.log' % args.model_number)


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
                                board, \
                                xfer_board, \
                                blk,cfg.inst.loc,cfg, \
                                grid_size=args.grid_size, \
                                num_iters=args.num_iters, \
                                cutoff=cutoff)

    else:
        raise Exception("unimplemented")

