from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib

from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import ops.generic_op as genoplib

import runtime.fit.model_fit as fitlib
import numpy as np

def update_delta_model(dev,delta_model,dataset):
    if dataset.method == llenums.ProfileOpType.INPUT_OUTPUT:
        rel = delta_model.get_subexpr(correctable_only=False)
    elif dataset.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
        rel = delta_model.get_subexpr(init_cond=True, \
                                      correctable_only=False, \
                                      concrete=False)
    elif dataset.method == llenums.ProfileOpType.INTEG_DERIVATIVE_GAIN:
        gain,offset = delta_model.get_subexpr(init_cond=False, \
                                      correctable_only=False, \
                                      concrete=False)
        if len(gain.vars()) == 0:
           print(delta_model.config)
           raise Exception("gain must have at least one variable")

        rel = gain

    elif dataset.method == llenums.ProfileOpType.INTEG_DERIVATIVE_STABLE:
        var_name = delta_model.spec.get_param_by_label(dataset.method.value)
        assert(not var_name is None)
        rel = genoplib.Var(var_name.name)

    elif dataset.method == llenums.ProfileOpType.INTEG_DERIVATIVE_BIAS:
        var_name = delta_model.spec.get_param_by_label(dataset.method.value)
        assert(not var_name is None)
        rel = genoplib.Var(var_name.name)

    else:
        return False,-1

    if not fitlib.fit_delta_model_to_data(delta_model, \
                                          rel, \
                                          dataset):
        return False,-1

    if dataset.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
        errors = delta_model.error(dataset, init_cond=True)
        return True, errors
    if dataset.method == llenums.ProfileOpType.INTEG_DERIVATIVE_BIAS:
        return True,[0.0]
    if dataset.method == llenums.ProfileOpType.INTEG_DERIVATIVE_STABLE:
        return True,[0.0]
    else:
        return True, delta_model.error(dataset)

def _get_delta_models(dev,blk,loc,output,config,orphans=True):
    delta_models = exp_delta_model_lib.get_models(dev, \
                                                  ['block','loc','output','static_config','hidden_config'],
                                                  block=blk, \
                                                  loc=loc, \
                                                  output=output, \
                                                  config=config) 
    if len(delta_models) == 0:
        if orphans:
            delta_models = [exp_delta_model_lib.ExpDeltaModel(blk, \
                                                              loc, \
                                                              output, \
                                                              config, \
                                                              llenums.CalibrateObjective.NONE)]
        else:
            delta_models = []

    return delta_models

def _update_delta_models_for_configured_block(dev,delta_models,blk,loc,output, \
                                              config, \
                                              force=False):
    model_errors = []
    noises= []
    for dataset in \
        exp_profile_dataset_lib.get_datasets(dev, \
                                           ['block','loc','output','static_config','hidden_config'],
                                           block=blk, loc=loc, output=output, config=config):
        #print("# data points %s (%s): %d" % (blk.name,dataset.method,len(dataset)))
        for delta_model in delta_models:
            succ,error = update_delta_model(dev,delta_model,dataset)
            noise = np.mean(dataset.meas_stdev)
            if succ:
               if dataset.method == llenums.ProfileOpType.INPUT_OUTPUT or \
                  dataset.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
                  model_errors.append(abs(error))
                  noises.append(noise)

    if len(model_errors) == 0:
        return False

    for delta_model in delta_models:
        avg_error = np.mean(model_errors)
        #print("avg-err: %f" % avg_error)
        delta_model.set_model_error(avg_error)
        delta_model.set_noise(noise)

        if delta_model.complete:
            print("%s %s %s" % (blk.name,loc,config.mode))
            print(delta_model)

        exp_delta_model_lib.update(dev,delta_model)

    return True

def update_delta_models_for_configured_block(dev,blk,loc,cfg, \
                                             force=False, \
                                             orphans=True):
    num_deltas = 0

    for output in blk.outputs:
        delta_models = _get_delta_models(dev,blk,loc,output,cfg,orphans=orphans)
        if all(map(lambda model: model.complete, delta_models)) and not force:
            continue

        for model in delta_models:
            model.clear()

        if _update_delta_models_for_configured_block(dev,delta_models,blk, \
                                                     loc,output, \
                                                     cfg, \
                                                     force=force):
                num_deltas += 1

def derive_delta_models_adp(args):
    board = runtime_util.get_device(args.model_number)
 
    if args.no_orphans:
       exp_delta_model_lib \
           .remove_models(board,['calib_obj'], \
                          calib_obj=llenums.CalibrateObjective.NONE)


    for blk,loc,cfg in exp_profile_dataset_lib \
        .get_configured_block_instances(board):
        update_delta_models_for_configured_block(board, \
                                                 blk, \
                                                 loc, \
                                                 cfg, \
                                                 force=args.force, \
                                                 orphans=not args.no_orphans)
