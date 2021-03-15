import ops.base_op as oplib
import runtime.fit.model_fit as modelfitlib
import ops.generic_op as genoplib
import ops.lambda_op as lamboplib
import numpy as np
import random
import itertools
import math

class RandomFunctionPool:

    def __init__(self,name,variables,penalty=0.01,max_params=10):
        self.name = name
        self.variables = variables
        self.ranges = {}
        self.pool = []
        self.gens = []

        self.scores = []
        self.errors = []
        self.raw_errors = []
        self.npars = []

        self.generation = 0
        self.penalty = penalty
        self.max_params = max_params

    def npts(self):
        return len(self.scores)

    def set_range(self,var,values):
        self.ranges[var] = values

    def get_params(self,expr):
        return list(set(filter(lambda v: 'par' in v, expr.vars())))

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
                    #print("[warn] cannot score function <%s>" % str(e))
                    continue

                if npars > self.max_params:
                    continue

                par_penalty = npars*self.penalty*median_ampl
                self.raw_errors[idx] = sumsq_err
                self.errors[idx] = np.mean(sumsq_err)
                self.scores[idx] = np.mean(self.errors[idx]) + par_penalty
                self.npars[idx] = npars

        # remove any functions that failed to fit
        indices = list(filter(lambda idx: not self.scores[idx] is None, \
                           range(self.npts())))
        self.scores = list(map(lambda idx: self.scores[idx],indices))
        self.errors = list(map(lambda idx: self.errors[idx],indices))
        self.raw_errors = list(map(lambda idx: self.raw_errors[idx],indices))
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

        for v in self.variables:
            rng = self.ranges[v]
            middle = np.mean(rng)
            scale = max(abs(max(rng)), abs(min(rng)))
            norm = lamboplib.Normalize(genoplib.Var(v), offset=middle, ampl=scale)
            #yield genoplib.Mult(genoplib.Var('par0'), norm)



    def initialize(self):
        self.pool = list(self.root_functions())
        self.scores = [None]*len(self)
        self.errors = [None]*len(self)
        self.raw_errors = [None]*len(self)
        self.npars = [None]*len(self)
        self.gens = [0]*len(self)

    # tournament selection
    def selection(self, exclude=[], k=10, p=0.5):
        indices = list(filter(lambda idx: not self.pool[idx] in exclude, \
                 range(len(self))))
        tourney = random.sample(indices, min(len(indices), k))
        subpool = list(map(lambda i: self.pool[i], tourney))
        subscores = list(map(lambda i: self.scores[i], tourney))

        tourney_sorted = np.argsort(subscores)
        prob = p
        for idx in tourney_sorted:
            if random.random() <= prob:
                yield subpool[idx]
            prob *= (1-p)



    def mutate(self,p):
        def const_expr(p):
           len(p.vars()) == 0 or \
              all(map(lambda n: "par" in n, p.vars()))
        
        par_idx = len(self.get_params(p))
        if not const_expr(p) and \
            all(map(lambda n: isinstance(n,genoplib.Var), p.nodes())):
                yield genoplib.Mult(lamboplib.SmoothStep(p.copy()), p.copy())

    def breed(self,p1,p2):
        def const_expr(p):
           len(p.vars()) == 0 or \
              all(map(lambda n: "par" in n, p.vars()))
        

        def product_expr(p):
            return all(map(lambda n: isinstance(n,genoplib.Var) or \
                    isinstance(n,genoplib.Mult) or \
                    isinstance(n,lamboplib.SmoothStep) or \
                    isinstance(n,lamboplib.Normalize), p.nodes()))

        par_idx = len(self.get_params(p1))
        p2_pars = self.get_params(p2)
        p2_repl = dict(map(lambda i: (p2_pars[i], \
                                 genoplib.Var('par%d' % (par_idx + i))), \
                           range(len(p2_pars))))

        p2_new = p2.substitute(p2_repl)

        if not const_expr(p1) or not const_expr(p2):
            yield genoplib.Add(p1.copy(), p2_new.copy())

        if product_expr(p1) and product_expr(p2_new):
            variables = ['par0']
            variables += list(filter(lambda v: not 'par' in v, p1.vars()))
            variables += list(filter(lambda v: not 'par' in v, p2_new.vars()))
            yield genoplib.product(list(map(lambda v: genoplib.Var(v), \
                                            variables)))

        #elif not const_expr(p1) and not const_expr(p2):
        #   yield genoplib.Mult(p1.copy(), p2_new.copy())



    def crossover(self,population):
        
        for p in population:
            for progeny in self.mutate(p):
                yield progeny

        indices = list(range(len(population)))
        for i,j in itertools.product(indices,indices):
            if i > j:
                continue
            p1,p2 = population[i],population[j]
            for progeny in self.breed(p1,p2):
                if len(self.get_params(progeny)) <= self.max_params:
                   yield progeny


    def add_unlabeled_function(self,new,generation):
        self.pool.append(new)
        self.scores.append(None)
        self.errors.append(None)
        self.raw_errors.append(None)
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

            for member in self.selection(exclude=list(pool.values())):
                if not str(member) in pool:
                    pool[str(member)] = member

        children = []
        self.generation += 1
        for new in self.crossover(list(pool.values())):
            self.add_unlabeled_function(new,self.generation)
            children.append(new)

        return list(pool.values()), children


    def get_best(self):
        idx = np.argmin(self.scores)
        return idx,self.scores[idx],self.gens[idx],self.pool[idx]

    def __len__(self):
        return len(self.pool)


