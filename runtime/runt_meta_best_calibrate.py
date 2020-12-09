import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.runtime_util as runtime_util
import hwlib.hcdc.llenums as llenums

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

def get_best_calibration(models):
    scores_by_calib = {}
    models_by_calib = {}
    for mdl in models:
        if mdl.calib_obj == llenums.CalibrateObjective.NONE:
            print("%s\ncalibration objective <%s> is none" \
                            % (mdl.config,mdl))
            continue

        obj = mdl.output.deltas[mdl.config.mode].objective
        score = obj.compute(mdl.variables())

        if mdl.calib_obj not in scores_by_calib:
            scores_by_calib[mdl.calib_obj] = []
            models_by_calib[mdl.calib_obj] = []

        scores_by_calib[mdl.calib_obj].append(score)
        models_by_calib[mdl.calib_obj].append(mdl)

    best_calib_obj = None
    for calib_obj,scores in scores_by_calib.items():
        score = sum(scores)
        if best_calib_obj is None or \
           sum(scores_by_calib[best_calib_obj]) > score:
            best_calib_obj = calib_obj

    print("=== best calib objective [%s] ===" % best_calib_obj)
    mdl = models_by_calib[best_calib_obj][0]
    print("  block=%s loc=%s mode=%s" % (mdl.block.name,mdl.loc,mdl.config.mode))
    print("  score=%s" % sum(scores_by_calib[best_calib_obj]))
    for mdl in models_by_calib[best_calib_obj]:
        print("  %s" % mdl)

    for model in models_by_calib[best_calib_obj]:
        new_model = model
        new_model.calib_obj = llenums.CalibrateObjective.BEST
        yield new_model

def calibrate(args):
    board = runtime_util.get_device(args.model_number)

    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.BEST)

    for models in group_by_configured_block(board):
        for best_mdl in get_best_calibration(models):
            exp_delta_model_lib.update(board,best_mdl)
