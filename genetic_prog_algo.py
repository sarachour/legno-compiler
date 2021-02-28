import runtime.runtime_meta_util as runtime_meta_util
import runtime.runtime_util as runtime_util
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib
import runtime.models.exp_delta_model as exp_delta_model_lib
from sklearn.linear_model import Ridge


import ops.base_op as oplib
import ops.generic_op as genoplib
import ops.lambda_op as lamboplib
import hwlib.hcdc.llenums as llenums
import numpy as np
import runtime.fit.model_fit as modelfitlib
import random
import itertools

class RandomFunctionPool:

    def __init__(self,variables):
        self.variables = variables
        self.ranges = {}
        self.pool = []
        self.scores = []
        self.gens = []
        self.generation = 0

    def set_range(self,var,values):
        self.ranges[var] = values

    def get_params(self,expr):
        return list(filter(lambda v: 'par' in v, expr.vars()))

    def score_one(self,expr,hidden_codes,values):
        params = self.get_params(expr)
        scores = []
        for loc,vals in values.items():
            hcs = dict(hidden_codes[loc])
            assert(all(map(lambda hc : len(vals) == len(hc), \
                           hcs.values())))

            data = {}
            data['inputs'] = hcs
            data['meas_mean'] = vals
            try:
                result = modelfitlib.fit_model(params,expr,data)
                params = result['params']
                preds = modelfitlib.predict_output(params,expr,data)
                sumsq = sum(map(lambda v: (v[0]-v[1])**2, zip(preds,vals)))
                scores.append(sumsq)


            except RuntimeError as e:
                if "Optimal parameters not found" in str(e):
                    scores.append(1e6)
                else:
                    raise e


        return len(params),scores

    def score(self,hidden_codes,values):
        for idx,fxn in enumerate(self.pool):
            if self.scores[idx] is None:
                npars,sumsq_err = self.score_one(fxn,hidden_codes,values)
                self.scores[idx] = npars*np.mean(sumsq_err)
                print("%d] gen=%d score=%f" % (idx,self.gens[idx], \
                                               self.scores[idx]))

    def root_functions(self):
        yield genoplib.Var('par0')

        for v in self.variables:
            yield genoplib.Mult(genoplib.Var('par0'), \
                             lamboplib.Pow(genoplib.Var(v), genoplib.Var('par1')))



    def initialize(self):
        self.pool = list(self.root_functions())
        self.scores = [None]*len(self)
        self.gens = [0]*len(self)

    # tournament selection
    def selection(self, k=10, p=0.5):
        indices = list(range(len(self)))
        tourney = random.sample(indices, min(len(indices), k))
        subpool = list(map(lambda i: self.pool[i], indices))
        subscores = list(map(lambda i: self.scores[i], indices))

        indices_sorted = np.argsort(subscores)
        prob = p
        for idx in indices_sorted:
            if random.random() <= prob:
                yield subpool[idx]
            prob *= (1-p)



    def breed(self,p1,p2):
        par_idx = len(self.get_params(p1))
        p2_pars = self.get_params(p2)
        p2_repl = dict(map(lambda i: (p2_pars[i], \
                                 genoplib.Var('par%d' % (par_idx + i))), \
                           range(len(p2_pars))))

        p2_new = p2.substitute(p2_repl)
        yield genoplib.Add(p1.copy(), p2_new.copy())
        yield genoplib.Mult(p1.copy(), p2_new.copy())

    def crossover(self,population):
        for p1,p2 in itertools.product(population,population):
            if str(p1) <= str(p2):
                continue

            for progeny in self.breed(p1,p2):
                yield progeny


    def evolve(self,pop_size=3):
        max_score = max(self.scores)
        pool = {}
        # choose parents
        for tries in range(100):
            if len(pool) >= pop_size:
                break

            for member in self.selection():
                if not str(member) in pool:
                    pool[str(member)] = member

        self.generation += 1
        print("parents: %d" % len(pool))
        for new in self.crossover(pool.values()):
            self.pool.append(new)
            self.scores.append(None)
            self.gens.append(self.generation)



    def get_best(self):
        idx = np.argmin(self.scores)
        print(self.scores[idx])
        return self.pool[idx]

    def __len__(self):
        return len(self.pool)


model_number = 'xfer'
block_name = 'integ'
mode = "(m,m,+)"
#block_name = 'integ'
#mode = "(m,m,+)"
#block_name = 'mult'
#mode = "(x,m,h)"

def get_repr_model(models):
    for loc,mdls in models.items():
        for cfg,mdl in mdls.items():
            return mdl

def find_functions(models,datasets,num_generations=5):
    repr_model = get_repr_model(models)
    model_pool = {}

    print("--- populating pool ---")
    for var in repr_model.variables():
        hidden_codes = list(dict(repr_model.hidden_codes()).keys())
        pool = RandomFunctionPool(hidden_codes)

        block = repr_model.block
        for hc in hidden_codes:
            pool.set_range(hc,block.state[hc].values)

        pool.initialize()
        model_pool[var] = pool
        print("%s #: %d" % (var, len(model_pool[var].pool)))


    print("--- extract dataset ---")
    hidden_configs = {}
    variables = dict(map(lambda v: (v,{}), repr_model.variables()))
    for loc,mdls in models.items():
        hidden_configs[loc] = dict(map(lambda v: (v[0],[]), \
                                       repr_model.hidden_codes()))
        for var in repr_model.variables():
            variables[var][loc] = []

        print("loc=%s cfgs=%d" % (loc,len(mdls.keys())))
        for st, mdl in mdls.items():
            for var in mdl.variables():
                variables[var][loc].append(mdl.get_value(var))
            for var,val in mdl.hidden_codes():
                hidden_configs[loc][var].append(val)

    print("--- score functions in pool ---")
    for var,pool in model_pool.items():
        print("-> %s (%d)" % (var,len(pool.pool)))
        pool.score(hidden_configs,variables[var])

    for idx in range(num_generations):
        print("--- evolve pool ---")
        for _,pool in model_pool.items():
            pool.evolve()

        print("--- score functions in pool ---")
        for var,pool in model_pool.items():
            print("-> %s (%d)" % (var,len(pool.pool)))
            pool.score(hidden_configs,variables[var])


    for var,pool in model_pool.items():
        yield var, pool.get_best()

board = runtime_util.get_device(model_number,layout=False)
block = board.get_block(block_name)
config = None
output = 'z'

datasets = {}
models = {}
print("-> getting models")
for model in  exp_delta_model_lib.get_all(board):
    if model.block.name == block_name and \
       str(model.config.mode) == mode and \
       str(model.output.name) == output:
        if not model.loc in models:
            models[model.loc] = {}
            datasets[model.loc] = {}

        models[model.loc][model.hidden_cfg] = model

print("-> getting datasets")
for data in exp_profile_dataset_lib.get_datasets(board):
    if data.block.name == block_name and \
       str(data.config.mode) == mode and \
       str(data.output.name) == output and \
       data.loc in models:
        datasets[data.loc][model.hidden_cfg] = data

functions = dict(find_functions(models,datasets))
print("========= BEST FUNCTIONS =========")
for var,expr in functions.items():
    print("var: %s" % var)
    print("   %s" % expr)
