import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.runtime_util as runtime_util
import numpy as np
import hwlib.hcdc.llenums as llenums


def bruteforce_calibrate(char_board):
    models = []
    scores = []
    for phys_model, score in runtime_meta_util \
        .homogenous_database_get_calibration_objective_scores(char_board):
        models.append(phys_model)
        scores.append(score)

    # find best bruteforce
    idxs = np.argsort(scores)
    best_idx = idxs[0]
    print("==== best models (score=%f) ====" % scores[best_idx])
    for model in models[best_idx]:
       model.calib_obj = llenums.CalibrateObjective.BRUTEFORCE
       print(model.config)
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
                .profile_block(board, \
                               model.block, \
                               model.loc, \
                               model.config, \
                               llenums.CalibrateObjective.BRUTEFORCE)
            runtime_meta_util.fit_delta_models(board)

