from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as delta_model_lib
import runtime.models.exp_profile_dataset as dataset_lib
import runtime.profile.visualize as vizlib
from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import util.paths as paths

def make_histogram(args):
    board = runtime_util.get_device(args.model_number,layout=True)
    ph = paths.DeviceStatePathHandler(board.name, \
                                  board.model_number,make_dirs=True)

    models = {}
    for exp_model in delta_model_lib.get_all(board):
        key = (exp_model.block, exp_model.output,\
               runtime_util.get_static_cfg(exp_model.block,exp_model.config), \
               exp_model.calib_obj)
        if not key in models:
            models[key] = []
        models[key].append(exp_model)

    for key,models in models.items():
        blk,out,cfg,lbl = key
        print("%s:%s = %d models" % (blk.name,cfg,len(models)))
        png_file = ph.get_histogram_vis('merr', \
                                        blk.name, \
                                        out.name, \
                                        cfg, \
                                        lbl)
        vizlib.model_error_histogram(models, \
                                     png_file, \
                                     num_bins=10)

        png_file = ph.get_histogram_vis('objf', \
                                        blk.name, \
                                        out.name, \
                                        cfg, \
                                        lbl)
        vizlib.objective_fun_histogram(models, \
                                       png_file, \
                                       num_bins=10)



def visualize(args):
    board = runtime_util.get_device(args.model_number,layout=True)
    label = llenums.CalibrateObjective(args.method)
    ph = paths.DeviceStatePathHandler(board.name, \
                                      board.model_number,make_dirs=True)
    make_histogram(args)
    for delta_model in delta_model_lib.get_all(board):
        if delta_model.complete and \
           delta_model.calib_obj != llenums.CalibrateObjective.NONE:
            png_file = ph.get_delta_vis(delta_model.block.name, \
                                        str(delta_model.loc), \
                                        str(delta_model.output.name), \
                                        str(delta_model.static_cfg), \
                                        str(delta_model.hidden_cfg), \
                                        delta_model.calib_obj)

            if delta_model.is_integration_op:
                dataset = dataset_lib.load(board, delta_model.block, \
                                           delta_model.loc, \
                                           delta_model.output, \
                                           delta_model.config, \
                                           llenums.ProfileOpType.INTEG_INITIAL_COND)
            else:
                dataset = dataset_lib.load(board, delta_model.block, \
                                           delta_model.loc, \
                                           delta_model.output, \
                                           delta_model.config, \
                                           llenums.ProfileOpType.INPUT_OUTPUT)

            if dataset is None:
                continue

            assert(isinstance(dataset, dataset_lib.ExpProfileDataset))
            vizlib.deviation(delta_model, \
                             dataset, \
                             png_file, \
                             baseline=vizlib.ReferenceType.MODEL_PREDICTION, \
                             num_bins=10, \
                             amplitude=None, \
                             relative=True)
