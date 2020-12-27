import runtime.profile.planner as planlib
import runtime.profile.profiler as proflib
import runtime.runtime_util as runtime_util

import hwlib.hcdc.llcmd_util as llutil
import hwlib.adp as adplib

def has_hidden_codes(block,loc,cfg):
  code = list(planlib.RandomCodeIterator(block,loc,cfg, \
                                         1))
  return len(code[0]) > 0

def characterize(runtime,board,block,cfg,locs, \
                 grid_size=7,  \
                 num_hidden_codes=200):
  print("=> characterizing %s" % block.name)
  for loc in locs:
    adp = adplib.ADP()
    adp.add_instance(block,loc)
    adp.configs.get(block.name,loc).set_config(cfg)

    adp = runtime_util.make_block_test_adp(board,adp,block,cfg)

    print("=== %s.%s ===" % (block.name,loc))
    print(cfg)
    print("grid-size: %d / num-codes: %d / num-locs: %d" % (grid_size, \
                                                            num_hidden_codes, \
                                                            len(locs)))
    if not has_hidden_codes(block,loc,cfg):
      return

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
                        proflib.profile_all_hidden_states(runtime, board, planner, adp=adp)

