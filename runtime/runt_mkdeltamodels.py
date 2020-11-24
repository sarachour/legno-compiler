from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib

from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import ops.generic_op as genoplib

import runtime.fit.model_fit as fitlib

def update_delta_model(dev,delta_model,dataset):
    if dataset.method == llenums.ProfileOpType.INPUT_OUTPUT:
        rel = delta_model.get_subexpr(correctable_only=False)
    elif dataset.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
        rel = delta_model.get_subexpr(init_cond=True, \
                                      correctable_only=False)
    elif dataset.method == llenums.ProfileOpType.INTEG_DERIVATIVE_GAIN:
        rel = delta_model.get_subexpr(init_cond=False, \
                                      correctable_only=False)
    else:
        return False,-1

    if not fitlib.fit_delta_model_to_data(delta_model, \
                                          rel, \
                                          dataset):
        return False,-1

    if dataset.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
        return True, delta_model.error(dataset, \
                                  init_cond=True)
    else:
        return True, delta_model.error(dataset)


def _update_delta_models_for_configured_block(dev,blk,loc,output,config,force=False):
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

    if all(map(lambda model: model.complete, delta_models)) and not force:
        return False

    model_errors = []
    for dataset in \
        exp_profile_dataset_lib.get_datasets_by_configured_block_instance(dev, \
                                                                          blk, \
                                                                          loc, \
                                                                          output, \
                                                                          config):
        print(dataset)
        print("# data points: %d" % len(dataset))
        for delta_model in delta_models:
            succ,error = update_delta_model(dev,delta_model,dataset)
        if succ:
            model_errors.append(abs(error))


    for delta_model in delta_models:
        avg_error = np.mean(model_errors)
        for err in model_errors:
            print("  err: %f" % err)
        print("avg-err: %f" % avg_error)
        delta_model.set_model_error(avg_error)
        if delta_model.complete:
            print(delta_model)
        exp_delta_model_lib.update(dev,delta_model)

    return True

def update_delta_models_for_configured_block(dev,blk,loc,cfg,hidden=True):
    num_deltas = 0
    for output in blk.outputs:
        for dataset in exp_profile_dataset_lib \
            .get_datasets_by_configured_block_instance(dev,blk,loc,output,cfg, \
                                                       hidden=hidden):
            if _update_delta_models_for_configured_block(dev,blk, \
                                                         loc,output, \
                                                         dataset.config):
                num_deltas += 1
    if num_deltas > 0:
        print(cfg)
        print("# updated deltas: %s" % num_deltas)


def derive_delta_models_adp(args):
    board = runtime_util.get_device(args.model_number)

    for blk,loc,cfg in exp_profile_dataset_lib \
        .get_configured_block_instances(board):
        update_delta_models_for_configured_block(board,blk,loc,cfg,hidden=True)
 
