import runtime.runtime_util as runtime_util
import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib
import runtime.fit.model_fit as modelfitlib

import hwlib.hcdc.llenums as llenums
import hwlib.block as blocklib
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


class MultiObjectiveResult:

    def __init__(self):
        self.values = []

    def add(self,val):
        self.values.append(val)

    # is this result pareto dominant over the other result.
    def dominant(self,other):
        dom = False
        for v1,v2 in zip(self.values,other.values):
            if v1 > v2:
                return False
            if v1 < v2:
                dom = True
        return dom

    def __repr__(self):
        return str(self.values)


class Predictor:

    '''
    This objective function encodes the block calibration objective. It maintains a
    consistent ordering of output port multi-objective functions.
    '''
    class ComplexObjective:

        def __init__(self):
            self._objectives = {}
            self._outputs = []

        def add(self,out,obj):
            self._outputs.append(out)
            self._objectives[out] = obj

        def __iter__(self):
            for out in self._outputs:
                for obj in self._objectives[out].objectives:
                    yield out,obj


    '''
    A subclass for managing the data the predictor parameters are
    elicited from
    '''
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


    '''
    The full symbolic predictor. This predictor is able to take a set of hidden codes
    and predict each of the sub-objective functions. We can then use the dominance test to choose the best one
    '''
    def __init__(self,blk,loc,cfg):
        self.variables = {}
        self.concrete_variables = {}
        self.objectives = Predictor.ComplexObjective()
        self.block = blk
        self.loc = loc
        self.config= cfg
        self.data = Predictor.Data(list(map(lambda o: o.name, self.block.outputs)), \
                                   runtime_util.get_hidden_codes(self.block))
        self.values = {}

    def predict(self,hidden_codes):
        delta_params = {}
        for (out,var),expr in self.concrete_variables.items():
            value = expr.compute(hidden_codes)
            # write predicted value to delta parameter dictionary
            if not out in delta_params:
                delta_params[out] = {}
            delta_params[out][var] = value

        objs = MultiObjectiveResult()
        for out,obj in self.objectives:
            val = obj.compute(delta_params[out])
            objs.add(val)

        return objs


    def add_objective(self,out,expr):
        assert(isinstance(expr,blocklib.DeltaSpec.MultiObjective))
        self.objectives.add(out.name,expr) 

    def set_variable(self,out,v,mdl):
        assert(not (out.name,v) in self.variables)
        self.variables[(out.name,v)] = mdl
        self.concrete_variables[(out.name,v)] = None
        self.data.add_variable(out,v)

    def min_samples(self):
        return max(map(lambda v: len(v.params) + 1, self.variables.values()))


    def fit(self):
        for  (out,var),model in self.variables.items():
            codes,values = self.data.get_dataset(self.block.outputs[out],var)
            if len(values) == 0:
                raise Exception("no data for fitting variable <%s> at output <%s>" % (var,out))

            print("TODO: test this with real data")
            #modelfitlib.fit_model(model.params,model.expr,{'inputs':codes,'meas_mean':values})
            self.values[(out,var)] = {}
            for par in model.params:
                self.values[(out,var)][par] = random.random()


            subst = dict(map(lambda tup: (tup[0],genoplib.Const(tup[1])), \
                             self.values[(out,var)].items()))
            conc_expr = model.expr.substitute(subst)
            self.concrete_variables[(out,var)] = conc_expr

''''
The pool of hidden codes to sample from when performing calibration.
The pool maintains a set of hidden codes and a symbolic predictor which guesses
the function value from the set of hidden code values

'''
class HiddenCodePool:

    class ParetoPoolView:

        def __init__(self,name):
            self.name = name
            self.values = []

        def add(self,v):
            assert(isinstance(v,MultiObjectiveResult))
            self.values.append(v)


    def __init__(self,variables,predictor):
        self.variables = variables
        self.predictor = predictor
        self.ranges = {}
        self.pool = []
        self.pool_keys = []

        self.meas_view = HiddenCodePool.ParetoPoolView('meas')
        self.pred_view = HiddenCodePool.ParetoPoolView('pred')

    def set_range(self,var,values):
        self.ranges[var] = values

    def random_sample(self):
        codes = {}
        for c in self.variables:
            codes[c] = random.choice(self.ranges[c])

        return codes

    def compute(self,delta_params):
        obj = MultiObjectiveResult()

        for out,subobj in self.predictor.objectives:
            pars = delta_params[out]
            val = subobj.compute(pars)
            obj.add(val)

        return obj

    def has_code(self,codes):
        key = runtime_util.dict_to_identifier(codes)
        return key in self.pool_keys

    def add_labeled_code(self,codes,values):
        key = runtime_util.dict_to_identifier(codes)
        if key in self.pool_keys:
            raise Exception("code already tested: %s score=%f" % (codes,score))

        self.pool_keys.append(key)

        meas = self.compute(values)
        pred = self.predictor.predict(codes)

        vals = list(map(lambda v: codes[v], self.variables))
        self.pool.append(vals)
        self.meas_view.add(meas)
        self.pred_view.add(pred)

    @property
    def ranking(self):
        for idx,key in enumerate(self.keys):
           yield self.scores[idx]
 
    def num_codes(self):
        return len(self.keys)

def insert_into_dict(d,ks,v):
    for k in ks[:-1]:
        if not k in d:
            d[k] = {}
        d = d[k]
    if not ks[-1] in d:
        d[ks[-1]] = []
    d[ks[-1]].append(v)


def load_code_pool_from_database(char_board,predictor):
    hidden_codes = list(map(lambda st: st.name, \
                            runtime_util.get_hidden_codes(predictor.block)))
    code_pool= HiddenCodePool(hidden_codes,predictor)
    # setting ranges of values in code pool
    for hc in hidden_codes:
        vals  = predictor.block.state[hc].values
        code_pool.set_range(hc,vals)

    by_output = {}
    for mdl in exp_delta_model_lib.get_all(char_board):
        insert_into_dict(by_output, [mdl.hidden_cfg], mdl)

    for _,mdls in by_output.items():
        codes = dict(mdl.hidden_codes())
        pred = code_pool.predictor.predict(codes)
        vs = {}
        for mdl in mdls:
            vs[mdl.output.name] = mdl.variables()

        actual = code_pool.compute(vs)

        print("hist %s" % (codes))
        print("   pred=%s" % pred)
        print("   meas=%s" % actual)
        if not code_pool.has_code(codes):
           code_pool .add_labeled_code(codes,vs)

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


'''
Build the symbolic predictor from the transfer learning data
and the block specification
'''
def build_predictor(xfer_board,block,loc,config):
    predictor = Predictor(block,loc,config)
    for output in block.outputs:
        phys_model = exp_phys_model_lib.load(xfer_board,block,config,output)
        for var,pmodel in phys_model.variables().items():
            predictor.set_variable(output,var,pmodel)

        predictor.add_objective(output, output.deltas[config.mode].objective)

    return predictor

'''
Update the predictor parameters with the characterization data
'''
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

def add_random_unlabelled_samples(pool,count):
    while True:
        samp = pool.random_sample()
        pred = pool.predictor.predict(samp)
        print("sample %s pred=%s" % (samp,pred))
        input()



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
    bootstrap_block(logger, \
                    char_board,block,loc,config, \
                    grid_size=grid_size, \
                    num_samples=nsamps_reqd)
    update_model(logger,char_board,block,loc,config)

    # fit all of the parameters in the predictor.
    update_predictor(predictor,char_board)

    # next, we're going to populate the initial pool of points.
    print("==== SETUP INITIAL POOL ====")
    code_pool= load_code_pool_from_database(char_board, predictor)
    add_random_unlabelled_samples(code_pool,10)
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

