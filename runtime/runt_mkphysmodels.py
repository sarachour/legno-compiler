from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib
import runtime.runt_mkdeltamodels as runt_mkdeltamodels
from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.block as blocklib
import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
import ops.interval as ivallib
from scipy.stats import pearsonr


import runtime.fit.model_fit as expr_fit_lib
import runtime.dectree.dectree_fit as dectree_fit_lib
import runtime.dectree.dectree as dectreelib
import runtime.dectree.dectree_nnfit as dectree_nn_fit_lib
import runtime.dectree.dectree_shrink as dectree_shrink_lib
import runtime.dectree.dectree_generalize as dectree_generalize_lib
import runtime.dectree.dectree_eval as dectree_eval
import runtime.dectree.dectree as dectreelib
import runtime.dectree.region as regionlib

import numpy as np
import json
import scipy

def add(dict_,key,value):
    if not key in dict_:
        dict_[key] = []
    dict_[key].append(value)

def update_dectree_data(blk,loc,exp_mdl, \
                        metadata, \
                        params, \
                        model_errors, \
                        hidden_code_fields, \
                        hidden_code_bounds, \
                        hidden_codes):

    key = (blk.name,loc,exp_mdl.static_cfg)
    if not key in params:
        params[key] = {}
        metadata[key] = (blk,loc,exp_mdl.config)
        model_errors[key] = []
        hidden_codes[key] = []
        hidden_code_fields[key] = []
        hidden_code_bounds[key] = {}

    for par,value in exp_mdl.params.items():
        add(params[key],par,value)
 

    for hidden_code,_ in exp_mdl.hidden_codes():
        if not hidden_code in hidden_code_fields[key]:
            hidden_code_bounds[key][hidden_code] = (blk.state[hidden_code].min_value, \
                                                    blk.state[hidden_code].max_value)
            hidden_code_fields[key].append(hidden_code)

    entry = [0]*len(hidden_code_fields[key])
    for hidden_code,value in exp_mdl.hidden_codes():
        idx = hidden_code_fields[key].index(hidden_code)
        entry[idx] = value

    hidden_codes[key].append(entry)
    model_errors[key].append(exp_mdl.model_error)



def get_ideal_value(model,var_name):
    # get the ideal value for the parameter
    delta_spec = list(model.block.outputs)[0].deltas[model.config.mode]
    if var_name == exp_delta_model_lib.ExpDeltaModel.MODEL_ERROR:
        return 0.0
    else:
        return delta_spec[var_name].val


def build_dectree(key,metadata, \
                  hidden_code_fields, \
                  hidden_code_bounds, \
                  hidden_codes,\
                  params, model_errors, \
                  local_model=False, \
                  num_points=20):

    blk,loc,cfg = metadata[key]
    n_samples = len(model_errors[key])
    #min_size = round(n_samples/num_leaves)
    print("--- fitting decision tree (%d samples) ---" % n_samples)
    hidden_code_fields_ = hidden_code_fields[key]
    hidden_code_bounds_ = hidden_code_bounds[key]
    hidden_codes_ = hidden_codes[key]
    model_errors_ = model_errors[key]

    model = exp_phys_model_lib.ExpPhysModel(blk,cfg)
    model.num_samples = n_samples

    print(cfg)

    print("==== MODEL ERROR ====")
    target_value = get_ideal_value(model,exp_phys_model_lib.ExpPhysModel.MODEL_ERROR) \
        if local_model else None
    dectree,predictions = dectree_nn_fit_lib.fit_decision_tree(hidden_code_fields_, \
                                                               hidden_code_bounds_,\
                                                               hidden_codes_, \
                                                               model_errors_, \
                                                               num_points, \
                                                               target_value=target_value)


    model.uncertainty.set_error(exp_phys_model_lib.ExpPhysModel.MODEL_ERROR,\
                                predictions,model_errors_)

    err = dectree_fit_lib.model_error(predictions,model_errors_)
    pct_err = err/max(np.abs(model_errors_))*100.0
    print("<<dectree>>: [[Model-Err]] err=%f pct-err=%f param-range=[%f,%f]" \
            % (err, pct_err, \
                min(model_errors_), \
                max(model_errors_)))


    for param,param_values in params[key].items():
        assert(len(param_values) == n_samples)
        target_value = get_ideal_value(model,param) if local_model else None

        print("==== PARAM %s ====" % param)
        dectree,predictions = dectree_nn_fit_lib.fit_decision_tree(hidden_code_fields_, \
                                                                   hidden_code_bounds_,\
                                                                   hidden_codes_, \
                                                                   param_values, \
                                                                   num_points, \
                                                                   target_value=target_value)

        err = dectree_fit_lib.model_error(predictions,param_values)
        model.uncertainty.set_error(param,\
                                    predictions,param_values)

        pct_err = err/max(np.abs(param_values))*100.0
        print("<<dectree>>: [[Param:%s]] err=%f pct-err=%f param-range=[%f,%f]" \
                % (param, err, pct_err, \
                    min(param_values), \
                    max(param_values)))
        assert(isinstance(dectree, dectreelib.RegressionLeafNode))
        model.set_param(param, dectree)


    return model

def get_hidden_code_intervals(phys_model):
    intervals = {}
    for st in filter(lambda st: isinstance(st.impl,blocklib.BCCalibImpl), \
                     phys_model.block.state):
        minval = min(st.values)
        maxval = max(st.values)
        intervals[st.name] = ivallib.Interval(minval,maxval)

    return intervals


def study_objective_fun(phys_model):
    blk = phys_model.block
    cfg = phys_model.config

    for var,mdl in phys_model.variables().items():
        expr = lambdoplib.Abs(genoplib.Var(var))
        nodes = dectree_eval.eval_expr(expr, {var:mdl})
        expr_tree = dectreelib.RegressionNodeCollection(nodes)
        minval,assigns = expr_tree.find_minimum()

        print("var %s: minimum=%f" % (var,minval))
        print("    %s" % assigns)

    for out in blk.outputs:
        calib_obj = out.deltas[cfg.mode].objective
        nodes = dectree_eval.eval_expr(calib_obj, phys_model.variables())
        objfun_dectree = dectreelib.RegressionNodeCollection(nodes)
        minval,assigns = objfun_dectree.find_minimum()

        print(calib_obj)
        print("minimum=%f" % (minval))
        print("    %s" % assigns)



def mktree(args):
    dev = runtime_util.get_device(args.model_number,layout=True)
    params = {}
    metadata = {}
    hidden_codes = {}
    hidden_code_fields = {}
    hidden_code_bounds = {}
    model_errors = {}
    for exp_mdl in exp_delta_model_lib.get_all(dev):
        blk = exp_mdl.block

        if not exp_mdl.complete:
            for dataset in exp_profile_dataset_lib.get_datasets_by_configured_block(dev, \
                                                                                    blk, \
                                                                                    exp_mdl.config, \
                                                                                    hidden=True):

                runt_mkdeltamodels.update_delta_model(dev,exp_mdl,dataset)

        if not exp_mdl.complete:
            print(exp_mdl.config)
            print("[WARN] incomplete delta model!")
            continue

        update_dectree_data(blk,exp_mdl.loc, \
                            exp_mdl, \
                            metadata,params,model_errors, \
                            hidden_code_fields, \
                            hidden_code_bounds, \
                            hidden_codes)


    models = {}
    tmpfile = "models.tmp"
    for key in model_errors.keys():
        (blk,loc,cfg) = key
        #num_leaves = min(pow(2,args.max_depth), \
        #                 args.num_leaves)
        new_model = build_dectree(key, \
                                  metadata, \
                                  hidden_code_fields, \
                                  hidden_code_bounds, \
                                  hidden_codes, \
                                  params, model_errors, \
                                  local_model=args.local_model, \
                                  num_points=args.num_points)
        if new_model is None:
            continue

        if not (blk,cfg) in models:
            models[(blk,cfg)] = []
        models[(blk,cfg)].append(new_model)

        with open(tmpfile,'a') as fh:
            fh.write("%s\n" % json.dumps(new_model.to_json()))

    print("==== Generalizing + Minimizing Models ===")
    for key,mdls in models.items():
        if len(mdls) == 0:
            continue

        print(mdls[0].config)
        '''
        if args.shrink:
            for mdl in mdls:
                print(str(key))
                intervals = get_hidden_code_intervals(mdl)
                for varname,dectree in mdl.variables().items():
                    print("orig   var=%s min-samps=%d" % (varname,dectree.min_sample()))
                    min_tree = dectree_shrink_lib.dectree_shrink(dectree,intervals)
                    print("shrink var=%s min-samps=%d" % (varname,min_tree.min_sample()))
                    mdl.set_variable(varname,min_tree)

                print("-----")
        '''

        print("num-models: %d" % len(mdls))
        if len(mdls) > 1:
            general_phys_model = dectree_generalize_lib.dectree_generalize(mdls)
        else:
            general_phys_model = mdls[0]

        #study_objective_fun(general_phys_model)
        exp_phys_model_lib.update(dev,general_phys_model)

