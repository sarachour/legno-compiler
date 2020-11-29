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
        rel = delta_model.get_subexpr(init_cond=False, \
                                      correctable_only=False, \
                                      concrete=False)
    else:
        return False,-1

    if not fitlib.fit_delta_model_to_data(delta_model, \
                                          rel, \
                                          dataset):
        print(delta_model.config)
        print(delta_model)
        print("can't fit model <%s>" % dataset.method)
        return False,-1

    if dataset.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
        return True, delta_model.error(dataset, init_cond=True)
    else:
        return True, delta_model.error(dataset)

def _get_delta_models(dev,blk,loc,output,config):
    delta_models = exp_delta_model_lib.get_fully_configured_outputs(dev, \
                                                                   blk, \
                                                                   loc, \
                                                                   output, \
                                                                   config)
    if len(delta_models) == 0:
        delta_models = [exp_delta_model_lib.ExpDeltaModel(blk, \
                                                        loc, \
                                                        output, \
                                                        config)]

    return delta_models

def _update_delta_models_for_configured_block(dev,delta_models,blk,loc,output,config,force=False):
    model_errors = []
    for dataset in \
        exp_profile_dataset_lib.get_datasets_by_configured_block_instance(dev, \
                                                                          blk, \
                                                                          loc, \
                                                                          output, \
                                                                          config):
        print("# data points %s (%s): %d" % (blk.name,dataset.method,len(dataset)))
        for delta_model in delta_models:
            succ,error = update_delta_model(dev,delta_model,dataset)
        if succ:
            if dataset.method == llenums.ProfileOpType.INPUT_OUTPUT or \
               dataset.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
               model_errors.append(abs(error))

    if len(model_errors) == 0:
        return False

    for delta_model in delta_models:
        avg_error = np.mean(model_errors)
        for err in model_errors:
            print("  err: %f" % err)
        print("avg-err: %f" % avg_error)
        delta_model.set_model_error(avg_error)
        if delta_model.complete:
            print("%s %s %s" % (blk.name,loc,config.mode))
            print(delta_model)
        exp_delta_model_lib.update(dev,delta_model)

    return True

def update_delta_models_for_configured_block(dev,blk,loc,cfg,hidden=True,force=False):
    num_deltas = 0

    for output in blk.outputs:
        delta_models = _get_delta_models(dev,blk,loc,output,cfg)
        if all(map(lambda model: model.complete, delta_models)) and not force:
            continue
        for model in delta_models:
            model.clear()

        for dataset in exp_profile_dataset_lib \
            .get_datasets_by_configured_block_instance(dev,blk,loc,output,cfg, \
                                                       hidden=hidden):
            if _update_delta_models_for_configured_block(dev,delta_models,blk, \
                                                         loc,output, \
                                                         dataset.config, force=force):
                num_deltas += 1

def derive_delta_models_adp(args):
    board = runtime_util.get_device(args.model_number)

    for blk,loc,cfg in exp_profile_dataset_lib \
        .get_configured_block_instances(board):
        update_delta_models_for_configured_block(board,blk,loc,cfg,hidden=True,force=args.force)
