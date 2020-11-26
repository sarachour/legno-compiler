from hwlib.adp import ADP,ADPMetadata

import runtime.models.exp_delta_model as delta_model_lib
import runtime.models.exp_profile_dataset as prof_dataset_lib
import runtime.profile.planner as planlib
import runtime.profile.profiler as proflib
import runtime.runtime_util as runtime_util

from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd

def profile_adp(args):
    board = runtime_util.get_device(args.model_number)
    adp = runtime_util.get_adp(board,args.adp)

    runtime = GrendelRunner()
    runtime.initialize()
    calib_obj = llenums.CalibrateObjective(args.method)
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            for exp_delta_model in delta_model_lib.get_calibrated(board, \
                                                                  blk, \
                                                                  cfg.inst.loc, \
                                                                  cfg, \
                                                                  calib_obj):

                for method,n,m,reps in runtime_util.get_profiling_steps(exp_delta_model.output, \
                                                                   exp_delta_model.config, \
                                                                   args.grid_size):

                    dataset = prof_dataset_lib.load(board,blk,cfg.inst.loc, \
                                                    exp_delta_model.output, \
                                                    exp_delta_model.config, \
                                                    method)

                    if not dataset is None and \
                    len(dataset) >= args.min_points and \
                    len(dataset) >= n*m*reps:
                        print("<===========")
                        print(cfg)
                        print("===> <%s> already profiled" % method)
                        continue

                    planner = planlib.SingleDefaultPointPlanner(blk, \
                                                                cfg.inst.loc, \
                                                                exp_delta_model.output, \
                                                                method, \
                                                                exp_delta_model.config,
                                                                n=n,
                                                                m=m, \
                                                                reps=reps)
                    proflib.profile_all_hidden_states(runtime,board,planner)


