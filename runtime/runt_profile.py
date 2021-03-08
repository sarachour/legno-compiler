from hwlib.adp import ADP,ADPMetadata

import runtime.models.exp_delta_model as delta_model_lib
import runtime.models.exp_profile_dataset as prof_dataset_lib
import runtime.profile.planner as planlib
import runtime.profile.profiler as proflib
import runtime.runtime_util as runtime_util

from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd

def profile_kernel(runtime,board,blk,cfg,calib_obj, \
                   min_points,max_points, \
                   grid_size,force=False,adp=None):
    for exp_delta_model in delta_model_lib.get_models(board, \
                                                          ['block','loc','static_config','calib_obj'],
                                                          block=blk, \
                                                          loc=cfg.inst.loc, \
                                                          config=cfg, \
                                                          calib_obj=calib_obj):

        for method,n,m,reps in runtime_util.get_profiling_steps(exp_delta_model.output, \
                                                                exp_delta_model.config, \
                                                                grid_size, \
                                                                max_points=max_points):

            dataset = prof_dataset_lib.load(board,blk,cfg.inst.loc, \
                                            exp_delta_model.output, \
                                            exp_delta_model.config, \
                                            method)
            print("<===========")
            print(cfg)
            print("===========>")
            print("output=%s method=%s" % (exp_delta_model.output.name,method));
            print("relation=%s" % (exp_delta_model.output.relation[cfg.mode]));
            print("dataset npts=%d" % (len(dataset) if not dataset is None else 0));
            print("n=%d m=%d reps=%d" % (n,m,reps))
            print("---------")
            if not dataset is None and \
            len(dataset) >= min_points and \
            len(dataset) >= n*m*reps and \
            not force:
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
            proflib.profile_all_hidden_states(runtime,board,planner,adp=adp)



def profile_adp(args):
    board = runtime_util.get_device(args.model_number)
    calib_obj = llenums.CalibrateObjective(args.method)
    runtime = GrendelRunner()

    runtime.initialize()
    if args.missing:
        for exp_delta_model in delta_model_lib.get_all(board):
            profile_kernel(runtime,board, \
                           exp_delta_model.block, \
                           exp_delta_model.config, \
                           calib_obj, \
                           min_points=args.min_points, \
                           grid_size=args.grid_size)

    else:
        adp = runtime_util.get_adp(board,args.adp,widen=args.widen)
        for cfg in adp.configs:
            blk = board.get_block(cfg.inst.block)
            cfg_modes = cfg.modes
            for mode in cfg_modes:
                cfg.modes = [mode]
                profile_kernel(runtime,board,blk,cfg,calib_obj, \
                               args.min_points, args.max_points, \
                               args.grid_size, \
                               force=args.force, adp=adp)
