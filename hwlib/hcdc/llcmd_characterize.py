import phys_model.planner as planlib
import phys_model.profiler as proflib
import hwlib.physdb as physdblib
import hwlib.hcdc.llcmd_util as llutil
import phys_model.model_fit as fitlib

def analyze_db(board):

	db = physdb.PhysicalDatabase(db_name)
	# build up dataset
	params = {}
	inputs = {}
	for blk in physdb.get_by_block_instance(db, dev,block,inst,cfg=cfg):
  		fitlib.analyze_physical_output(blk)
	return


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
    planner = planlib.RandomPlanner(block, loc, cfg,
                                    n=grid_size,
                                    m=grid_size,
                                    num_codes=num_hidden_codes)
    proflib.profile_all_hidden_states(runtime, board, planner)
    print(" -> analyzing")
    physdblib.get_by_block_instance(board.physdb, \
                                    board,block,loc,cfg=cfg)
    fitlib.analyze_physical_output(blk)

