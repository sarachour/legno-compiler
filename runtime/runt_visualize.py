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
                                     num_bins=10, \
                                     relative=True)

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
    calib_obj = llenums.CalibrateObjective(args.calib_obj)
    ph = paths.DeviceStatePathHandler(board.name, \
                                      board.model_number,make_dirs=True)
    if args.histogram:
        make_histogram(args)

    for delta_model in delta_model_lib.get_all(board):
        if delta_model.calib_obj != calib_obj:
            continue

        if delta_model.complete and \
           delta_model.calib_obj != llenums.CalibrateObjective.NONE:
            
            print(delta_model.config)
            print(delta_model)
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
                print("-> no dataset")
                continue

            assert(isinstance(dataset, dataset_lib.ExpProfileDataset))
            png_file = ph.get_delta_vis(delta_model.block.name, \
                                        delta_model.loc.file_string(),\
                                        str(delta_model.output.name), \
                                        str(delta_model.static_cfg), \
                                        str(delta_model.hidden_cfg), \
                                        delta_model.calib_obj)
            print(png_file)
            vizlib.deviation(delta_model, \
                             dataset, \
                             png_file, \
                             baseline=vizlib.ReferenceType.MODEL_PREDICTION, \
                             num_bins=10, \
                             amplitude=args.max_error, \
                             relative=True)

            png_file = ph.get_correctable_delta_vis(delta_model.block.name, \
                                                    delta_model.loc.file_string(), \
                                                    str(delta_model.output.name), \
                                                    str(delta_model.static_cfg), \
                                                    str(delta_model.hidden_cfg), \
                                                    delta_model.calib_obj)
            print(png_file)
            vizlib.deviation(delta_model, \
                             dataset, \
                             png_file, \
                             baseline=vizlib.ReferenceType.CORRECTABLE_MODEL_PREDICTION, \
                             num_bins=10, \
                             amplitude=args.max_error, \
                             relative=True)

            model_file = ph.get_model_file(delta_model.block.name, \
                                           delta_model.loc.file_string(), \
                                           str(delta_model.output.name), \
                                           str(delta_model.static_cfg), \
                                           str(delta_model.hidden_cfg), \
                                           delta_model.calib_obj)

            with open(model_file,'w') as fh:
                fh.write(str(delta_model.config))
                fh.write(str(delta_model))
                fh.write("\n\n")
                fh.write(str(delta_model.spec))
