import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.runtime_util as runtime_util
import numpy as np
import hwlib.hcdc.llenums as llenums


def bruteforce_calibrate(char_board):
    scores = {}
    models = {}
    for model in exp_delta_model_lib.get_all(char_board):
        calib_obj = model.output.deltas[model.config.mode].objective
        variables = model.variables()
        if not all(map(lambda v : v in variables, calib_obj.vars())):
           continue

        if not model.hidden_cfg in models:
           models[model.hidden_cfg] = []
           scores[model.hidden_cfg] = 0.0

        score = calib_obj.compute(variables)
        models[model.hidden_cfg].append(model)
        scores[model.hidden_cfg] += score

        print("=== model score=%f ===" % score)
        print(model)

    # find best bruteforce
    hidden_codes = list(models.keys())
    idxs = np.argsort(list(map(lambda hc: scores[hc], hidden_codes)))
    best_idx = idxs[0]
    print("==== best models (score=%f) ====" % scores[hidden_codes[best_idx]])
    for model in models[hidden_codes[best_idx]]:
       model.calib_obj = llenums.CalibrateObjective.BRUTEFORCE
       print(model)
       yield model

def calibrate(args):
    board = runtime_util.get_device(args.model_number)
    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.BEST)
    exp_delta_model_lib \
        .remove_by_calibration_objective(board,llenums.CalibrateObjective.BRUTEFORCE)

    for dbname in runtime_meta_util.get_block_databases(args.model_number):
        char_board = runtime_util.get_device(dbname,layout=False)
        if runtime_meta_util.database_is_empty(char_board):
            continue

        runtime_meta_util.fit_delta_models(char_board)
        # make sure the database only concerns one configured block

        if not (runtime_meta_util.database_is_homogenous(char_board,enable_outputs=True)):
            continue

        # fitting any outstanding delta models
        # get the best model from bruteforcing operation
        for idx,model in enumerate(bruteforce_calibrate(char_board)):
           print("======#### BEST MODEL ####=======")
           print(model)
           # update the original database to include the best brute force model
           exp_delta_model_lib.update(board,model)

           if idx == 0:
            # profile bruteforce model if you haven't already
            runtime_meta_util \
                .profile_block(board,model.block, \
                               model.loc, \
                               model.config, \
                               llenums.CalibrateObjective.BRUTEFORCE)
            runtime_meta_util.fit_delta_models(board)

