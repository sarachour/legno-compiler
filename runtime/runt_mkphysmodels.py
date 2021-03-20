import runtime.runtime_meta_util as runtime_meta_util
import runtime.runtime_util as runtime_util
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.mkphys_pass.function_pool as fxnlib

import hwlib.hcdc.llenums as llenums

import argparse
import numpy as np

class ModelErrorVar:

    def __init__(self,*indices):
        self.indices = indices

    def __repr__(self):
        idx = ",".join(map(lambda i: str(i), self.indices))
        return "model-err(%s)" % idx

def find_best_function(pool, \
                       var_name, hidden_codes,values, \
                       num_generations=5,pop_size=5,penalty=0.001,max_params=4,debug=False):


    print("--- initially score functions in pool ---")
    pool.score(hidden_codes,values)

    for generation in range(num_generations):
        print("---- generation %d/%d ----" \
              % (generation,num_generations))

        print("--- evolve pool ---")
        parents,children = pool.evolve(pop_size=pop_size)
        print("evolve var=%s parents=%d children=%d" \
              % (var_name, len(parents),len(children)))


        print("--- scoring pool ---")
        pool.score(hidden_codes,values)

    index,score,gen,expr = pool.get_best()
    print("var=%s score=%s gen=%d npars=%d" \
        % (var_name,score,gen,pool.npars[index]))
    print("  %s" % str(pool.raw_errors[index]))

    index,score,gen,expr = pool.get_best()
    print("===  best model for %s ===" % var_name)
    print("generation=%d index=%d" % (index,gen))
    print("score=%s" % score)
    print("expr=%s" % expr)
    print("")
    return index,score,gen,expr


def make_pool(repr_model,variable,penalty=0.001,max_params=4):
    hidden_codes = list(dict(repr_model.hidden_codes()).keys())
    pool = fxnlib.RandomFunctionPool(variable, \
                                     hidden_codes, \
                                     penalty=penalty, \
                                     max_params=max_params)

    block = repr_model.block
    for hc in hidden_codes:
        pool.set_range(hc,block.state[hc].values)

    pool.initialize()

    return hidden_codes,pool

def find_error_model_functions(physical_model,models,num_generations=5,pop_size=5,penalty=0.001,max_params=4,debug=False):
    repr_model = get_repr_model(models)
    if repr_model is None:
       raise Exception("no representative model found. (# models=%d)" % len(models))

    model_pool = {}

    print("############################")
    print(repr_model.config)
    print("############################")
    print("--- populating model errors ---")
    for index,block_inputs in repr_model.model_error.points():
        model_error_var = ModelErrorVar(index)
        print(index,model_error_var)
        hidden_codes,pool = make_pool(repr_model,model_error_var, \
                                      penalty=penalty,max_params=max_params)


        print("number of functions=%d" % len(pool))
        print("-> collating values of model error <%s>" % model_error_var)
        values = {}
        hcs = {}
        npts = 0
        for loc,mdls in models.items():
            hcs[loc] = dict(map(lambda hc: (hc,[]), hidden_codes))
            values[loc] = []
            for mdl in filter(lambda m: m.complete, mdls.values()):
                for var,val in mdl.hidden_codes():
                    hcs[loc][var].append(val)

                values[loc].append(mdl.model_error.get_error(block_inputs))
                npts += 1

        print("-> fitting function for model_error <%s> npts=%d" % (model_error_var,npts))
        ident,score,gen,expr = find_best_function(pool, \
                                                                model_error_var, \
                                                                hcs, \
                                                                values, \
                                                                num_generations=5, \
                                                                pop_size=5, \
                                                                penalty=0.001, \
                                                                max_params=4, \
                                                                debug=False)

        physical_model.model_error.set_expr(index=index,expr=expr,error=score)


def find_delta_variable_functions(physical_model,models,num_generations=5,pop_size=5,penalty=0.001,max_params=4,debug=False):
    repr_model = get_repr_model(models)
    if repr_model is None:
       raise Exception("no representative model found. (# models=%d)" % len(models))

    model_pool = {}

    print("############################")
    print(repr_model.config)
    print("############################")
    print("--- populating model errors ---")
    for delta_var in repr_model.variables():
        hidden_codes,pool = make_pool(repr_model,delta_var, \
                                      penalty=penalty,max_params=max_params)


        print("number of functions=%d" % len(pool))
        print("-> collating values of model error <%s>" % delta_var)
        values = {}
        hcs = {}
        npts = 0
        for loc,mdls in models.items():
            hcs[loc] = dict(map(lambda hc: (hc,[]), hidden_codes))
            values[loc] = []
            for mdl in filter(lambda m: m.complete, mdls.values()):
                for var,val in mdl.hidden_codes():
                    hcs[loc][var].append(val)

                values[loc].append(mdl.get_value(delta_var))
                npts += 1

        print("-> fitting function for model_error <%s> npts=%d" % (delta_var,npts))
        index,score,gen,expr = find_best_function(pool, \
                                                                delta_var, \
                                                                hcs, \
                                                                values, \
                                                                num_generations=5, \
                                                                pop_size=5, \
                                                                penalty=0.001, \
                                                                max_params=4, \
                                                                debug=False)

        physical_model.set_variable(name=delta_var,expr=expr,error=score)


def find_all_functions(physical_model,models,num_generations=5,pop_size=5,penalty=0.001,max_params=4,debug=False):
    find_delta_variable_functions(physical_model, \
                                  models,num_generations=num_generations, \
                                  pop_size=pop_size, \
                                  penalty=penalty, \
                                  max_params=max_params)


    find_error_model_functions(physical_model, \
                               models,num_generations=num_generations, \
                               pop_size=pop_size, \
                               penalty=penalty, \
                               max_params=max_params)



def get_repr_model(models):
    for loc,mdls in models.items():
        for cfg,mdl in mdls.items():
            return mdl



def genetic_infer_model(board,block,config,output,models,datasets, \
                        num_generations=1, pop_size=1,penalty=0.001,max_params=4,force=False):


   existing_models = exp_phys_model_lib.get_models(board,['block','static_config','output'],block, config, output)

   if len(existing_models) > 0 and not force:
      print(config)
      print("[warn] already exists, returning!")
      return

   #if block.name == "fanout" or block.name == "integ" or str(config.mode) != "(x,m,h)":
    #  return

   repr_model = get_repr_model(models)
   if repr_model is None:
       raise Exception("no representative model found. (# models=%d)" % len(models))


   # make a physical model with the same dimensions of the delta model
   pmdl = exp_phys_model_lib.ExpPhysModel(block,config,output, \
                                          n=repr_model.model_error.n)

   find_all_functions(pmdl,models, \
                      num_generations=num_generations, \
                      pop_size=pop_size \
                      ,penalty=penalty, \
                      max_params=max_params)

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
                            max_params=args.max_params, \
                            force=args.force)
