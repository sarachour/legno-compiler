import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.runtime_util as runtime_util
import numpy as np
import hwlib.hcdc.llenums as llenums


def bruteforce_calibrate(char_board):
    scores = []
    models = []
    for model in exp_delta_model_lib.get_all(char_board):
        calib_obj = model.output.deltas[model.config.mode].objective
        score = calib_obj.compute(model.variables())
        models.append(model)
        scores.append(score)

        print("=== model score=%f ===" % score)
        print(model)
    if len(models) < 200:
       return None

    # find best bruteforce
    idxs = np.argsort(scores)
    best_idx = idxs[0]
    print("==== best model (score=%f) ====" % scores[best_idx])
    models[best_idx].calib_obj = llenums.CalibrateObjective.BRUTEFORCE
    print(models[best_idx])
    return models[best_idx]

def calibrate(args):
    board = runtime_util.get_device(args.model_number)
    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.BEST)
    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.BRUTEFORCE)

    for dbname in runtime_meta_util.get_block_databases(args.model_number):
        char_board = runtime_util.get_device(dbname,layout=False)
        runtime_meta_util.fit_delta_models(char_board)
        # make sure the database only concerns one configured block
        assert(runtime_meta_util.database_is_homogenous(char_board))
        # fitting any outstanding delta models
        # get the best model from bruteforcing operation
        best_model = bruteforce_calibrate(char_board)
        if best_model is None:
           continue

        print(best_model)
        # update the original database to include the best brute force model
        exp_delta_model_lib.update(board,best_model)
        # profile bruteforce model if you haven't already
        runtime_meta_util \
            .profile(board,char_board,llenums.CalibrateObjective.BRUTEFORCE)
        runtime_meta_util.fit_delta_models(board)

