import runtime.runtime_meta_util as runtime_meta_util
import runtime.runtime_util as runtime_util
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.mkphys_pass.function_pool as fxnlib

import hwlib.hcdc.llenums as llenums

import argparse
import numpy as np



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
        pool = fxnlib.RandomFunctionPool(var,hidden_codes, \
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
        pool.score(hidden_configs,variables[var])

    for generation in range(num_generations):
        print("---- generation %d/%d ----" \
              % (generation,num_generations))
        for var, pool in model_pool.items():
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
            if debug:
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



def get_repr_model(models):
    for loc,mdls in models.items():
        for cfg,mdl in mdls.items():
            return mdl



def genetic_infer_model(board,block,config,output,models,datasets, \
                        num_generations=1, pop_size=1,penalty=0.001,max_params=4):
   functions = dict(find_functions(models,num_generations=num_generations,pop_size=pop_size,penalty=penalty,max_params=max_params))
   pmdl = exp_phys_model_lib.ExpPhysModel(block,config,output)

   print("===== BEST FUNCTIONS ======")
   print(config)
   print("")
   for var,(score,expr) in functions.items():
       print("var: %s" % var)
       print("   %s score=%f" % (expr,score))
       pmdl.set_variable(var,expr,score)

   if block.name == "adc" or block.name == "dac":
        input("continue")

   if len(functions) > 0:
      exp_phys_model_lib.update(board, pmdl)
   #input("done!")



def preprocess_board_data(board):
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

    return models,datasets


def execute(args):
    board = runtime_util.get_device(args.model_number)

    models_ds, datasets_ds = preprocess_board_data(board)

    for key in models_ds.keys():
        models =models_ds[key]
        datasets = datasets_ds[key]
        repr_model = get_repr_model(models)

        if repr_model is None:
            raise Exception("no representative model found. (# models=%d)" % len(models_b))

        genetic_infer_model(board, \
                            repr_model.block, \
                            repr_model.config, \
                            repr_model.output, \
                            models,datasets, \
                            num_generations=args.generations, \
                            pop_size=args.parents,  \
                            penalty=args.penalty, \
                            max_params=args.max_params)
