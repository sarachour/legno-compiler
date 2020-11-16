from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib

from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd

import runtime.fit.model_fit as fitlib

def update_delta_model(dev,delta_model,dataset):
    if dataset.method == llenums.ProfileOpType.INPUT_OUTPUT:
        rel = delta_model.relation
    elif dataset.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
        rel = delta_model.relation.init_cond
    elif dataset.method == llenums.ProfileOpType.INTEG_DERIVATIVE_GAIN:
        rel = delta_model.relation.deriv
    else:
        return

    if not fitlib.fit_delta_model_to_data(delta_model, \
                                   rel, \
                                   dataset):
        return

    print(rel)
    new_error = delta_model.model_error
    if dataset.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
        new_error += delta_model.error(dataset, \
                                  init_cond=True)
    else:
        new_error += delta_model.error(data.inputs, \
                                       data.meas_mean)

    delta_model.set_model_error(new_error)
    exp_delta_model_lib.update(dev,delta_model)

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

        if not delta_model.complete:
            update_delta_model(board,delta_model,dataset)
            print(delta_model)

