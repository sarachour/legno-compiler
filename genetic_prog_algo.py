import runtime.runtime_meta_util as runtime_meta_util
import runtime.runtime_util as runtime_util
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
from sklearn.linear_model import Ridge
import argparse

import ops.base_op as oplib
import ops.generic_op as genoplib
import ops.lambda_op as lamboplib
import hwlib.hcdc.llenums as llenums
import numpy as np
import runtime.fit.model_fit as modelfitlib
import random
import itertools

class RandomFunctionPool:

    def __init__(self,name,variables,penalty=0.01,max_params=10):
        self.name = name
        self.variables = variables
        self.ranges = {}
        self.pool = []
        self.gens = []

        self.scores = []
        self.errors = []
        self.npars = []

        self.generation = 0
        self.penalty = penalty
        self.max_params = max_params

    def npts(self):
        return len(self.scores)

    def set_range(self,var,values):
        self.ranges[var] = values

    def get_params(self,expr):
        return list(filter(lambda v: 'par' in v, expr.vars()))

    def score_one(self,expr,hidden_codes,values):
        params = self.get_params(expr)
        scores = []

        for loc,vals in values.items():
            hcs = dict(hidden_codes[loc])
            assert(all(map(lambda hc: len(hc) == len(vals), hcs.values())))

            data = {}
            data['inputs'] = hcs
            data['meas_mean'] = vals
            try:
                result = modelfitlib.fit_model(params,expr,data)
                params = result['params']
                preds = modelfitlib.predict_output(params,expr,data)
                sumsq = sum(map(lambda v: (v[0]-v[1])**2, zip(preds,vals)))/len(preds)
                scores.append(sumsq)


            except RuntimeError as e:
                raise Exception("exception: %s" % str(e))


        return len(params),scores

    def score(self,hidden_codes,values):
        median_ampl = np.median(list(map(lambda v: np.median(np.abs(v)), \
                                         values.values())))

        for idx,fxn in enumerate(self.pool):
            if self.scores[idx] is None:
                try:
                   npars,sumsq_err = self.score_one(fxn,hidden_codes,values)
                except Exception as e:
                    print("[warn] cannot score function <%s>" % str(e))
                    continue

                if npars > self.max_params:
                    continue

                par_penalty = npars*self.penalty*median_ampl
                self.errors[idx] = np.mean(sumsq_err)
                self.npars[idx] = npars
                self.scores[idx] = self.errors[idx] + par_penalty
                print("%f] %s" % (self.errors[idx],fxn))
                print("  %s" % str(sumsq_err))
        # remove any functions that failed to fit
        indices = list(filter(lambda idx: not self.scores[idx] is None, \
                           range(self.npts())))
        self.scores = list(map(lambda idx: self.scores[idx],indices))
        self.errors = list(map(lambda idx: self.errors[idx],indices))
        self.npars = list(map(lambda idx: self.npars[idx],indices))
        self.pool = list(map(lambda idx: self.pool[idx],indices))
        self.gens= list(map(lambda idx: self.gens[idx],indices))

    def get_all(self,ranked_only=False,since=None):
        for idx,fxn in enumerate(self.pool):
            if self.scores[idx] is None and ranked_only:
                continue
            if not since is None and self.gens[idx] < since:
                continue

            yield self.gens[idx],self.scores[idx],fxn


    def root_functions(self):
        yield genoplib.Var('par0')

        for v in self.variables:
            yield genoplib.Mult(genoplib.Var('par0'), genoplib.Var(v))

        if False:
            for v in self.variables:
                for v2 in self.variables:
                    yield genoplib.Mult(genoplib.Var('par0'), 
                                                genoplib.Mult(genoplib.Var(v), genoplib.Var(v2)))


        if False:
            for v in self.variables:
                for v2 in self.variables:
                    yield genoplib.Add( \
                                        genoplib.Mult(genoplib.Var('par0'), genoplib.Var(v))
                                        , genoplib.Mult(genoplib.Var('par1'), genoplib.Var(v2)))

        if False:
            for v in self.variables:
                yield genoplib.Mult(genoplib.Var('par0'), \
                                lamboplib.Pow(genoplib.Var(v), genoplib.Var('par1')))



    def initialize(self):
        self.pool = list(self.root_functions())
        self.scores = [None]*len(self)
        self.errors = [None]*len(self)
        self.npars = [None]*len(self)
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

        if all(map(lambda n: not isinstance(n,genoplib.Add), p1.nodes())) and \
           all(map(lambda n: not isinstance(n,genoplib.Add),p2.nodes())):
            yield genoplib.Mult(p1.copy(), p2_new.copy())

    def crossover(self,population):
        for p1,p2 in itertools.product(population,population):
            if str(p1) <= str(p2):
                continue

            for progeny in self.breed(p1,p2):
                yield progeny


    def add_unlabeled_function(self,new,generation):
        self.pool.append(new)
        self.scores.append(None)
        self.errors.append(None)
        self.npars.append(None)
        self.gens.append(self.generation)

    def evolve(self,pop_size=3):
        if len(self.scores) == 0:
            raise Exception("the sample pool is empty.")

        max_score = max(self.scores)
        pool = {}
        # choose parents
        for tries in range(1000):
            if len(pool) >= pop_size:
                break

            for member in self.selection():
                if not str(member) in pool:
                    pool[str(member)] = member

        children = []
        self.generation += 1
        for new in self.crossover(pool.values()):
            self.add_unlabeled_function(new,self.generation)
            children.append(new)

        return list(pool.values()), children


    def get_best(self):
        idx = np.argmin(self.scores)
        return idx,self.scores[idx],self.gens[idx],self.pool[idx]

    def __len__(self):
        return len(self.pool)


#block_name = 'integ'
#mode = "(m,m,+)"
#block_name = 'mult'
#mode = "(x,m,h)"

def get_repr_model(models):
    for loc,mdls in models.items():
        for cfg,mdl in mdls.items():
            return mdl

def find_functions(models,num_generations=5,pop_size=5,penalty=0.001,max_params=4,debug=False):
    repr_model = get_repr_model(models)
    if repr_model is None:
       raise Exception("no representative model found. (# models=%d)" % len(models))

    model_pool = {}

    print("############################")
    print(repr_model.config)
    print("############################")

    print("--- populating pool ---")
    for var in repr_model.variables():
        hidden_codes = list(dict(repr_model.hidden_codes()).keys())
        pool = RandomFunctionPool(var,hidden_codes, \
                                  penalty=penalty, \
                                  max_params=max_params)

        block = repr_model.block
        for hc in hidden_codes:
            pool.set_range(hc,block.state[hc].values)

        pool.initialize()
        model_pool[var] = pool
        print("%s #: %d" % (var, len(pool.pool)))


    print("--- extract dataset ---")
    hidden_configs = {}
    variables = dict(map(lambda v: (v,{}), repr_model.variables()))
    for loc,mdls in models.items():
        hidden_configs[loc] = dict(map(lambda v: (v[0],[]), \
                                       repr_model.hidden_codes()))
        for var in repr_model.variables():
            variables[var][loc] = []

        npts = 0
        for st, mdl in mdls.items():
            if not mdl.complete:
                continue

            for var in mdl.variables():
                variables[var][loc].append(mdl.get_value(var))

            for var,val in mdl.hidden_codes():
                hidden_configs[loc][var].append(val)
                npts += 1

        print("# datapoints [%s]: %d" % (loc,npts))

    print("--- initially score functions in pool ---")
    for var,pool in model_pool.items():
        print("-> %s (%d)" % (var,len(pool.pool)))
        pool.score(hidden_configs,variables[var])

    for generation in range(num_generations):
        print("---- generation %d/%d ----" \
              % (generation,num_generations))
        for var, pool in model_pool.items():
            print("-> %s (%d)" % (var,len(pool.pool)))
            if debug:
                for idx,(gen,score,fxn) in enumerate(pool.get_all(since=generation)):
                    print("%d] gen=%d score=%f expr=%s" % (idx,gen, \
                                                        score, fxn))

        print("--- evolve pool ---")
        for delta_var,pool in model_pool.items():
            parents,children = pool.evolve(pop_size=pop_size)
            print("evolve var=%s parents=%d children=%d" \
                  % (delta_var, len(parents),len(children)))
 

        print("--- scoring pool ---")
        for var,pool in model_pool.items():
            pool.score(hidden_configs,variables[var])

        for var,pool in model_pool.items():
            index,score,gen,expr = pool.get_best()
            print("var=%s score=%s gen=%d expr=%s" %  (var,score,gen,expr))



    print("---- finalizing pool and getting best codes ----")
    print("   -> identify lowest number of parameters")
    max_pars = 0
    for var,pool in model_pool.items():
        index,score,gen,expr = pool.get_best()
        max_pars = max(max_pars, pool.npars[index])

    print("number of parameters=%d" % max_pars)
    print("   -> choose best function with no parameter penalty")
    for var,pool in model_pool.items():
        indices = list(filter(lambda idx: pool.npars[idx] <= max_pars, \
                              range(pool.npts())))
        best_idx = np.argmin(list(map(lambda idx: pool.errors[idx], indices)))
        yield var,(pool.errors[best_idx],pool.pool[best_idx])






def genetic_infer_model(board,block,config,output,models,datasets,num_generations=1, pop_size=1,penalty=0.001,max_params=4):
   functions = dict(find_functions(models,num_generations=num_generations,pop_size=pop_size,penalty=penalty,max_params=max_params))
   pmdl = exp_phys_model_lib.ExpPhysModel(block,config,output)

   print("===== BEST FUNCTIONS ======")
   print(config)
   print("")
   for var,(score,expr) in functions.items():
       print("var: %s" % var)
       print("   %s score=%f" % (expr,score))
       pmdl.set_variable(var,expr,score)

   if len(functions) > 0:
      exp_phys_model_lib.update(board, pmdl)
   #input("done!")


def execute(board,num_generations=1,pop_size=1,penalty=0.001,max_params=4):
    def insert(d,ks):
        for k in ks:
            if not k in d:
                d[k] = {}
            d = d[k]

    datasets = {}
    models = {}

    for model in exp_delta_model_lib.get_all(board):
        keypath = [(model.block.name, str(model.config.mode),model.output.name), \
                   model.loc]
        insert(models,keypath)
        insert(datasets,keypath)
        models[keypath[0]][keypath[1]][model.hidden_cfg] = model
        datasets[keypath[0]][keypath[1]][model.hidden_cfg] = None

    for data in exp_profile_dataset_lib.get_all(board):
        keypath = [(data.block.name, str(data.config.mode),data.output.name), \
                   data.loc]
        insert(datasets,keypath)
        datasets[keypath[0]][keypath[1]][data.hidden_cfg] = data

    for key in models.keys():
        models_b = models[key]
        datasets_b = datasets[key]
        repr_model = get_repr_model(models_b)
        if repr_model is None:
            raise Exception("no representative model found. (# models=%d)" % len(models_b))

        genetic_infer_model(board,repr_model.block,repr_model.config,repr_model.output, \
                            models_b,datasets_b,num_generations=num_generations, pop_size=pop_size, penalty=penalty, max_params=max_params)


parser = argparse.ArgumentParser(description='Physical model inference script.')
parser.add_argument('model_number', type=str,help='physical model database to analyze')
parser.add_argument('--penalty',default=0.01, \
                       type=float,help='parameter penalty')
parser.add_argument('--max_params',default=3, \
                       type=int,help='maximum number of physical model parameters')
parser.add_argument('--generations',default=5, \
                       type=int,help='generations to execute for')
parser.add_argument('--parents',default=25, \
                       type=int,help='number of progenators to select per generation')

args = parser.parse_args()

board = runtime_util.get_device(args.model_number)
execute(board, num_generations=args.generations, \
        pop_size=args.parents, \
        max_params=args.max_params, \
        penalty=args.penalty)
