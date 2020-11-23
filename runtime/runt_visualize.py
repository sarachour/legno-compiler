from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as delta_model_lib
import runtime.models.exp_profile_dataset as dataset_lib
import runtime.profile.visualize as vizlib
from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import util.paths as paths

def visualize(args):
    board = runtime_util.get_device(args.model_number,layout=True)
    label = llenums.CalibrateObjective(args.method)
    ph = paths.DeviceStatePathHandler(board.name, \
                                      board.model_number,make_dirs=True)

    for delta_model in delta_model_lib.get_all(board):
        if delta_model.complete:
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
                             num_bins=15, \
                             amplitude=None, \
                             relative=True)
