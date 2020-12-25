import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.runtime_util as runtime_util
import hwlib.hcdc.llenums as llenums
import numpy as np

def group_by_configured_block(board):
    instances = {}
    for model in exp_delta_model_lib.get_all(board):
        key = (model.block.name, \
               str(model.loc), \
               model.static_cfg)
        if not key in instances:
            instances[key] = []

        instances[key].append(model)

    return instances.values()

def get_best_calibration(all_models):

    scores = []
    models = []
    for mdls,score in runtime_meta_util \
        .get_calibration_objective_scores(all_models):
        scores.append(score)
        models.append(mdls)
        
        print("%s" % mdls[0])
        print("  score=%f" % score)
        print("")

    inds = np.argsort(scores)
    best_idx = inds[0]

    best_models = models[best_idx]
    print("===== best model (score=%f) ===" % scores[best_idx])
    for mdl in models[best_idx]:
        mdl.calib_obj = llenums.CalibrateObjective.BEST
        print(mdl)
        yield mdl

def calibrate(args):
    board = runtime_util.get_device(args.model_number)

    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.BEST)

    for models in group_by_configured_block(board):
        print("===== block =====")
        print(models[0].config)
        print("")
        for best_mdl in get_best_calibration(models):
            exp_delta_model_lib.update(board,best_mdl)
