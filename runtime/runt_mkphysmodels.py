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
import ops.interval as ivallib
from scipy.stats import pearsonr


import runtime.fit.model_fit as expr_fit_lib
import runtime.dectree.dectree_fit as dectree_fit_lib
import runtime.dectree.dectree_shrink as dectree_shrink_lib
import runtime.dectree.dectree_generalize as dectree_generalize_lib
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



def build_local_dataset(model,var_name,codes,values,num_points):
    if len(values) <= num_points:
        return codes,values

    # get the ideal value for the parameter
    delta_spec = list(model.block.outputs)[0].deltas[model.config.mode]
    if var_name == "modelError":
        target_val = 0
    else:
        target_val = delta_spec[var_name].val

    # choose the data points closest to that parameter.
    scores = list(map(lambda v: abs(v-target_val), values))
    indices = np.argsort(scores)

    new_values = list(map(lambda i: values[i], \
                          indices[:num_points]))
    new_codes = list(map(lambda i: codes[i], \
                         indices[:num_points]))
    return new_codes,new_values

class ErrorCovarianceEstimator:

    def __init__(self):
        self.errors = {}
        self.joint = []

    def set_error(self,v,pred,obs):
        n = min(len(pred),len(obs))
        self.errors[v] = list(map(lambda i: (pred[i]-obs[i]), \
                                  range(n)))


    def verify_covariance(self):
        n_samps = 100
        n_vars = len(self.variables)
        dataset = list(map(lambda v: [], range(n_vars)))

        samps = np.random.multivariate_normal(mean=self.mean.reshape(n_vars,), \
                                      cov=self.covariance, \
                                      size=n_samps)
        for samp in samps:
            for idx,val in enumerate(samp):
                dataset[idx].append(val)
            print(dict(zip(self.variables,samp)))
        print("\n\n")
        cov = np.cov(dataset,bias=True)
        print("\n\n")
        print(self.mean)
        print("\n\n")
        print(cov)

    def estimate_covariance(self):
        self.variables = list(self.errors.keys())
        data = list(map(lambda v: self.errors[v], self.variables))
        self.covariance = np.cov(data,bias=True)
        self.mean = np.array(list(map(lambda v: np.mean(self.errors[v]), \
                                      self.variables)))
        print("\n\n")
        print(self.mean)
        print("\n\n")
        print(self.covariance)

def build_dectree(key,metadata, \
                  hidden_code_fields, \
                  hidden_code_bounds, \
                  hidden_codes,\
                  params, model_errors, \
                  num_leaves,max_depth, \
                  local_model=False, \
                  num_points=10):

    blk,loc,cfg = metadata[key]
    n_samples = len(model_errors[key])
    min_size = round(n_samples/num_leaves)
    print("--- fitting decision tree (%d samples) ---" % n_samples)
    hidden_code_fields_ = hidden_code_fields[key]
    hidden_code_bounds_ = hidden_code_bounds[key]
    hidden_codes_ = hidden_codes[key]
    model_errors_ = model_errors[key]

    model = exp_phys_model_lib.ExpPhysModel(blk,cfg)
    model.num_samples = n_samples

    print(cfg)
    if local_model:
        codes,values = build_local_dataset(model, \
                                           exp_phys_model_lib.ExpPhysModel.MODEL_ERROR, \
                                           hidden_codes_, model_errors_,num_points)
    else:
        codes,values = hidden_codes_, model_errors_

    dectree,predictions = dectree_fit_lib.fit_decision_tree(hidden_code_fields_, \
                                                    codes, \
                                                    values, \
                                                    bounds=hidden_code_bounds_, \
                                                    max_depth=max_depth, \
                                                    min_size=min_size)

    model.uncertainty.set_error(exp_phys_model_lib.ExpPhysModel.MODEL_ERROR,\
                                predictions,values)

    err = dectree_fit_lib.model_error(predictions,values)
    pct_err = err/max(np.abs(values))*100.0
    print("<<dectree>>: [[Model-Err]] err=%f pct-err=%f param-range=[%f,%f]" \
            % (err, pct_err, \
                min(model_errors_), \
                max(model_errors_)))


    for param,param_values in params[key].items():
        assert(len(param_values) == n_samples)
        if local_model:
            codes,values = build_local_dataset(model,param, \
                                               hidden_codes_, param_values,num_points)
        else:
            codes,values = hidden_codes_, param_values

        dectree,predictions = dectree_fit_lib.fit_decision_tree(hidden_code_fields_, \
                                                                codes, \
                                                                values, \
                                                                bounds=hidden_code_bounds_, \
                                                                max_depth=max_depth, \
                                                                min_size=min_size)

        err = dectree_fit_lib.model_error(predictions,values)
        model.uncertainty.set_error(param,\
                                    predictions,values)

        pct_err = err/max(np.abs(values))*100.0
        print("<<dectree>>: [[Param:%s]] err=%f pct-err=%f param-range=[%f,%f]" \
                % (param, err, pct_err, \
                    min(param_values), \
                    max(param_values)))
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
        num_leaves = min(pow(2,args.max_depth), \
                         args.num_leaves)

        new_model = build_dectree(key, \
                                  metadata, \
                                  hidden_code_fields, \
                                  hidden_code_bounds, \
                                  hidden_codes, \
                                  params, model_errors, \
                                  num_leaves=num_leaves,\
                                  max_depth=args.max_depth, \
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

        print("num-models: %d" % len(mdls))
        if len(mdls) > 1:
            general_phys_model = dectree_generalize_lib.dectree_generalize(mdls)
        else:
            general_phys_model = mdls[0]

        exp_phys_model_lib.update(dev,general_phys_model)

