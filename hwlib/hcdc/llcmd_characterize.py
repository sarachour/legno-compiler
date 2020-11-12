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


def characterize(runtime,board,block,cfg):
  locs = llutil.random_locs(board,block,10)
  print("=> characterizing %s" % block.name)
  for loc in locs:
    print("=== %s.%s ===" % (block.name,loc))
    print(cfg)
    planner = planlib.RandomPlanner(block, loc, cfg,
                                    n=8,
                                    m=10,
                                    num_codes=1000)
    proflib.profile_all_hidden_states(runtime, board, planner)
    print(" -> analyzing")
    physdblib.get_by_block_instance(board.physdb, \
                                    board,block,loc,cfg=cfg)
    fitlib.analyze_physical_output(blk)

