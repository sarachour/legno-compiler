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


def derive_delta_models_adp(args):
    board = runtime_util.get_device(args.model_number)

    for dataset in exp_profile_dataset_lib \
        .get_datasets(board):


        delta_model = exp_delta_model_lib.load(board, \
                                            dataset.block, \
                                            dataset.loc, \
                                            dataset.output, \
                                            dataset.config)
        if delta_model is None:
            delta_model = exp_delta_model_lib.ExpDeltaModel(dataset.block, \
                                                         dataset.loc, \
                                                         dataset.output, \
                                                         dataset.config)

        if delta_model.complete:
            continue

        model_error = 0.0
        for datum in exp_profile_dataset_lib.get_datasets_by_configured_block(board, \
                                                          dataset.block, \
                                                          dataset.loc, \
                                                          dataset.output, \
                                                          dataset.config):
            succ,error = update_delta_model(board,delta_model,datum)
            if succ:
                model_error += error

        delta_model.set_model_error(model_error)
        exp_delta_model_lib.update(board,delta_model)
        if delta_model.complete:
            print(delta_model)
