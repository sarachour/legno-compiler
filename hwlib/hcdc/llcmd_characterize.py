import runtime.profile.planner as planlib
import runtime.profile.profiler as proflib
import runtime.runtime_util as runtime_util

import hwlib.hcdc.llcmd_util as llutil

def characterize(runtime,board,block,cfg,locs, \
                 grid_size=7,  \
                 num_hidden_codes=200):
  print("=> characterizing %s" % block.name)
  for loc in locs:
    print("=== %s.%s ===" % (block.name,loc))
    print(cfg)
    print("grid-size: %d / num-codes: %d / num-locs: %d" % (grid_size, \
                                                            num_hidden_codes, \
                                                            len(locs)))

    random_hidden_codes = list(planlib.RandomCodeIterator(block,loc,cfg, \
                                                          num_hidden_codes))
    for hidden_code in random_hidden_codes:
        for output in block.outputs:
                for method,n,m,reps in runtime_util.get_profiling_steps(output,cfg,grid_size):
                        planner = planlib.SingleTargetedPointPlanner(block,  \
                                                                     loc,  \
                                                                     output, \
                                                                     cfg, \
                                                                     method,
                                                                     n=n,
                                                                     m=m,
                                                                     reps=reps,
                                                                     hidden_codes=hidden_code)
                        proflib.profile_all_hidden_states(runtime, board, planner)

