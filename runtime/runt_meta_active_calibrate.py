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
        self.errors = []

    def add(self,val,error=0.0):
        assert(isinstance(error,float))
        self.values.append(val)
        self.errors.append(error)

    # is this result pareto dominant over the other result.
    def dominant(self,other):
        dom = False
        assert(len(self.errors) > 0)
        for v1,e1,v2,e2 in zip(self.values,self.errors,other.values,other.errors):
            if v1+e1 > v2-e2:
                return False
            if v1-e1 < v2+e2:
                dom = True
        return dom

    def __repr__(self):
        return str(self.values)

    def __iter__(self):
        for v in self.values:
            yield v

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
        self.errors = {}

    def predict(self,hidden_codes):
        delta_params = {}
        delta_errors = {}
        for (out,var),expr in self.concrete_variables.items():
            value = expr.compute(hidden_codes)
            # write predicted value to delta parameter dictionary
            if not out in delta_params:
                delta_params[out] = {}
                delta_errors[out] = {}
            delta_params[out][var] = value
            delta_errors[out][var] = self.errors[(out,var)]

        objs = MultiObjectiveResult()
        for out,obj in self.objectives:
            val = obj.compute(delta_params[out])
            err = genoplib.propagate_error(obj,delta_errors[out])
            objs.add(val,error=err)

        return objs


    def add_objective(self,out,expr):
        assert(isinstance(expr,blocklib.DeltaSpec.MultiObjective))
        self.objectives.add(out.name,expr) 

    def set_variable(self,out,v,mdl):
        assert(not (out.name,v) in self.variables)
        if mdl is None:
            raise Exception("no physical model for <%s> of output <%s>" % (v,out.name))
        self.variables[(out.name,v)] = mdl
        self.data.add_variable(out,v)

    def min_samples(self):
        return max(map(lambda v: len(v.params) + 1, self.variables.values()))


    def fit(self):
        for (out,var),model in self.variables.items():
            codes,values = self.data.get_dataset(self.block.outputs[out],var)
            npts = len(values)
            if len(values) == 0:
                raise Exception("no data for fitting variable <%s> at output <%s>" % (var,out))

            try:
               result = modelfitlib.fit_model(model.params,model.expr,{'inputs':codes,'meas_mean':values})
            except Exception as e:
               print("[WARN] failed to predict <%s> for output <%s> of block <%s>" % (var,out,self.block.name))
               print("   %s.%s deltavar=%s expr=%s" % (self.block.name,out,var, model.expr))
               print("   codes=%s" % str(codes))
               print("  values=%s" % str(values))
               print("  exception=%s" % e)
               continue

            self.values[(out,var)] = {}
            for par in model.params:
                self.values[(out,var)][par] = result['params'][par]

            subst = dict(map(lambda tup: (tup[0],genoplib.Const(tup[1])), \
                             self.values[(out,var)].items()))
            conc_expr = model.expr.substitute(subst)
            self.concrete_variables[(out,var)] = conc_expr

            error = 0.0
            for idx in range(npts):
               pred = conc_expr.compute(dict(map(lambda hc: (hc,codes[hc][idx]), self.data.hidden_codes)))
               error += (values[idx]-pred)**2
            self.errors[(out,var)] = math.sqrt(error)/npts
            print("%s.%s deltavar=%s expr=%s" % (self.block.name,out,var,conc_expr))
            print("   codes=%s" % str(codes))
            print("   pars=%s" % str(result['params']))
            print("   values=%s" % str(values))
            print("   errors=%s" % str(result['param_error']))
            print("")
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
            assert(isinstance(v,MultiObjectiveResult) or v is None)
            self.values.append(v)

        def get_best(self):
            v = self.values[0]
            best_idx = 0
            for idx,value in enumerate(self.values):
                if value.dominant(v):
                    v = value
                    best_idx = idx
            return best_idx,v


        def is_dominant(self,res):
            for v in self.values:
                if not res.dominant(v):
                    print("not dominant!")
                    print("res: %s" % (str(res)))
                    print("val: %s" % (str(v)))
                    return False
            return True


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

    def get_values(self,v):
        return self.ranges[v]

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

    def get_unlabeled(self):
        for mv,p in zip(self.meas_view.values,self.pool):
            if mv is None:
                yield dict(zip(self.variables,p))

    def add_unlabeled_code(self,codes):
        key = runtime_util.dict_to_identifier(codes)
        if key in self.pool_keys:
            raise Exception("code already tested: %s score=%f" % (codes,score))

        self.pool_keys.append(key)

        pred = self.predictor.predict(codes)
        vals = list(map(lambda v: codes[v], self.variables))
        self.pool.append(vals)
        self.meas_view.add(None)
        self.pred_view.add(pred)


    def affix_label_to_code(self,codes,values):
        key = runtime_util.dict_to_identifier(codes)
        assert(key in self.pool_keys)
        idx = self.pool_keys.index(key)
        if not self.meas_view.values[idx] is None:
            print(self.meas_view.values[idx])
            raise Exception("there is already a label for this code <%s>" % (str(codes)))

        meas = self.compute(values)
        self.meas_view.values[idx] = meas


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
    print("===== Database Models ====")
    for mdl in exp_delta_model_lib.get_all(char_board):
        print(mdl)
        insert_into_dict(by_output, [mdl.hidden_cfg], mdl)

    print("===== Initial Code Pool ====")
    for _,mdls in by_output.items():
        codes = dict(mdl.hidden_codes())
        pred = code_pool.predictor.predict(codes)
        vs = {}
        for mdl in mdls:
            vs[mdl.output.name] = mdl.variables()

        actual = code_pool.compute(vs)

        print("hist %s" % (codes))
        for (_,expr),pred,act in zip(code_pool.predictor.objectives,pred,actual):
            print("  obj=%s pred=%f meas=%f" % (expr,pred,act))

        if not code_pool.has_code(codes):
           code_pool .add_labeled_code(codes,vs)

    return code_pool


def update_model(logger,char_board,blk,loc,cfg):
    #"python3 grendel.py mkphys --model-number {model} --max-depth 0 --num-leaves 1 --shrink" 
    CMDS = [ \
             "python3 grendel.py mkdeltas --model-number {model} --force > deltas.log" \
    ]


    adp_file = runtime_meta_util.generate_adp(char_board,blk,loc,cfg)

    runtime_sec = 0
    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=char_board.full_model_number)
        print(">> %s" % cmd)
        runtime_sec += runtime_meta_util.run_command(cmd)

    logger.log('upd_mdl',runtime_sec)

    runtime_meta_util.remove_file(adp_file)


'''
Do some initial bootstrapping to fit the elicited models.
'''
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


def profile_block(logger,board,blk,loc,cfg,grid_size=9,calib_obj=llenums.CalibrateObjective.NONE):
    CMDS = [ \
             "python3 grendel.py prof {adp} --model-number {model} --grid-size {grid_size} {calib_obj} > profile.log" \
            ]

    adp_file = runtime_meta_util.generate_adp(board,blk,loc,cfg)

    runtime_sec = 0
    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=board.full_model_number, \
                         grid_size=grid_size, \
                         calib_obj=calib_obj.value)
        print(">> %s" % cmd)
        runtime_sec += runtime_meta_util.run_command(cmd)

    logger.log('profile',runtime_sec)
    runtime_meta_util.remove_file(adp_file)


def write_model_to_database(logger,pool,board,char_board):
    idx,score = pool.meas_view.get_best()
    code_values = pool.pool[idx]
    hidden_codes = dict(zip(pool.variables, \
                            code_values))

    new_config = pool.predictor.config.copy()
    for var,value in hidden_codes.items():
        new_config[var].value = value


    exp_delta_model_lib.remove_models(board, \
                                      ['block','loc','static_config','hidden_config','calib_obj'], \
                                      block=pool.predictor.block, \
                                      loc=pool.predictor.loc, \
                                      config=new_config,  \
                                      calib_obj=llenums.CalibrateObjective.MODELBASED)

    for dataset in exp_profile_dataset_lib.get_datasets(char_board, \
                                                        ['block','loc','static_config','hidden_config'], \
                                                        block=pool.predictor.block, \
                                                        loc=pool.predictor.loc, \
                                                        config=new_config):
        exp_profile_dataset_lib.update(board,dataset)


    for model in exp_delta_model_lib.get_models(char_board, \
                                                ['block','loc','static_config','hidden_config'], \
                                                block=pool.predictor.block, loc=pool.predictor.loc, \
                                                config=new_config):
        model.calib_obj = llenums.CalibrateObjective.MODELBASED
        exp_delta_model_lib.update(board,model)

'''
This function takes a point and evaluates it in the hardware to identify
the delta model parameters. These labels are attached.
'''
def query_hidden_codes(logger,pool,board,blk,loc,cfg,hidden_codes,grid_size=9):
    new_cfg = cfg.copy()
    for var,value in hidden_codes.items():
        int_value = blk.state[var].nearest_value(value)
        new_cfg[var].value = int_value

    for out in blk.outputs:
        exp_model = exp_delta_model_lib.ExpDeltaModel(blk,loc,out,new_cfg, \
                                                      calib_obj=llenums.CalibrateObjective.NONE)
        exp_delta_model_lib.update(board,exp_model)

    profile_block(logger,board,blk,loc,new_cfg,grid_size)
    update_model(logger,board,blk,loc,new_cfg)

    mdls = exp_delta_model_lib.get_models_by_fully_configured_block_instance(board,blk,loc,new_cfg)
    assert(len(mdls) > 0)
    vs = {}
    for mdl in mdls:
        vs[mdl.output.name] = mdl.variables()

    codes = dict(mdl.hidden_codes())
    actual = pool.compute(vs)
    pred = pool.predictor.predict(codes)
    print("samp %s" % (codes))
    for (_,expr),pred,act in zip(pool.predictor.objectives,pred,actual):
        print("  obj=%s pred=%f meas=%f" % (expr,pred,act))


    assert(pool.has_code(codes))
    pool .affix_label_to_code(codes,vs)


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
def update_predictor(predictor,char_board,nsamples):
     assert(predictor.min_samples() <= nsamples)

     for model in exp_delta_model_lib.get_all(char_board):
        if nsamples == 0:
            break

        for var,val in model.variables().items():
            predictor.data.add_datapoint(model.output, var,  \
                                         dict(model.hidden_codes()), val)

        nsamples -= 1

     predictor.fit()

'''
Randomly probe some samples and print out the predictions.
'''
def get_sample(pool,slack=0.02):
    def compatible(prim,second):
        for v,val in second.items():
            if v in prim and prim[v] != val:
                return False
        return True

    # figure out what the lower bound on the pool is for each subobjective
    min_vals = pool.pred_view.values[0]
    for vals in pool.pred_view.values:
        min_vals = list(map(lambda tup: min(*tup), zip(min_vals,vals)))

    # compute constraints over hidden codes
    solutions = []
    solution_scores = []
    variables = []
    for idx,((out,obj), min_val) in enumerate(zip(pool.predictor.objectives,min_vals)):

        # first derive a concrete expression for the subobjective
        # mapping hidden codes to objective function values
        vdict = {}
        for (out2,var),expr in pool.predictor.concrete_variables.items():
            if out2 == out:
                vdict[var] = expr

        conc_obj = obj.substitute(vdict)

        # next iterate over all possible combinations of hidden codes
        # and score them according to how far they are over the limit
        free_vars = list(conc_obj.vars())
        values = list(map(lambda v: pool.get_values(v), free_vars))
        options = list(itertools.product(*values))
        scores = []
        for vs in options:
            vdict = dict(zip(free_vars,vs))
            scores.append(conc_obj.compute(vdict) - min_val)

        #wrhite these data points to the collection of solutions
        indices = np.argsort(scores)
        variables.append(free_vars)
        valid_options = []
        valid_scores = []
        for idx in indices:
            if scores[idx] < slack:
                valid_options.append(options[idx])
                valid_scores.append(scores[idx])

        solutions.append(valid_options)
        solution_scores.append(valid_scores)

    keys = []
    for order in itertools.permutations(list(range(len(solutions)))):
        vdict = {}
        failed=False
        for idx in order:
            found = False
            pos = 0
            while not failed and not found and pos < len(solutions[idx]):
                subdict = dict(zip(variables[idx],solutions[idx][pos]))
                if compatible(vdict,subdict):
                    for v,val in subdict.items():
                        vdict[v] = val
                    found=True

                pos += 1

            if not found:
                failed = True

        key = runtime_util.dict_to_identifier(vdict)
        if not failed and not key in keys:
            print("=> success!")
            keys.append(key)
            print(vdict)
            yield vdict


    print("-> done")

def add_random_unlabelled_samples(pool,count):
    npts = 0
    for constraint in get_sample(pool):
        if npts > count:
            return

        samp = pool.random_sample()
        for var,val in constraint.items():
            samp[var] = val

        print(samp)
        pool.add_unlabeled_code(samp)
        npts += 1


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
    nsamps_reqd = predictor.min_samples()*2+1

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
    update_predictor(predictor,char_board,nsamps_reqd)

    # next, we're going to populate the initial pool of points.
    print("==== SETUP INITIAL POOL ====")
    code_pool= load_code_pool_from_database(char_board, predictor)

    #TODO: maybe put this in a loop?
    print("==== ADD UNLABELLED ====")
    add_random_unlabelled_samples(code_pool,10)

    print("==== QUERY UNLABELLED ====")
    for hcs in code_pool.get_unlabeled():
       query_hidden_codes(logger,code_pool,char_board,block,loc,config,hcs)

    write_model_to_database(logger,code_pool, board,char_board)

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

