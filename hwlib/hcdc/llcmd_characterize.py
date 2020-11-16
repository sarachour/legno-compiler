import runtime.profile.planner as planlib
import runtime.profile.profiler as proflib
import runtime.runtime_util as runtime_util

import hwlib.hcdc.llcmd_util as llutil

def characterize(runtime,board,block,cfg,grid_size=7,  \
                 num_hidden_codes=200, \
                 num_locs=5):
  locs = llutil.random_locs(board,block,num_locs)
  print("=> characterizing %s" % block.name)
  for loc in locs:
    print("=== %s.%s ===" % (block.name,loc))
    print(cfg)
    print("grid-size: %d / num-codes: %d / num-locs: %d" % (grid_size, \
                                                            num_hidden_codes, \
                                                            num_locs))
    for output in block.outputs:
        for method,n,m in runtime_util.get_profiling_steps(output,cfg,grid_size):
                planner = planlib.RandomPlanner(block, loc, output, cfg, method,
                                                n=n,
                                                m=m,
                                                num_codes=num_hidden_codes)
                proflib.profile_all_hidden_states(runtime, board, planner)

