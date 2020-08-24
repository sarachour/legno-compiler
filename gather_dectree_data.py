import hwlib.hcdc.hcdcv2 as hcdclib
import phys_model.lin_dectree as lindectree
import target_block
import hwlib.physdb as physdb
from lab_bench.grendel_runner import GrendelRunner
import phys_model.profiler as proflib
import phys_model.planner as planlib
from analyze import analyze_db

import json

with open("dectree.json") as fh:
  serialized_dectree_dict = json.load(fh)

dectree = lindectree.DecisionNode.from_json(serialized_dectree_dict)

with open("predictions.json") as fh:
  predictions = json.load(fh)



sample_list = []
dectree.random_sample(sample_list)

dev = hcdclib.get_device()
block, inst, cfg = target_block.get_block(dev)
db = physdb.PhysicalDatabase('board6')
runtime = GrendelRunner()


for current_sample_dict in sample_list:
	planner = planlib.SingleTargetedPointPlanner(block,inst,cfg,10,current_sample_dict)
	proflib.profile_all_hidden_states(runtime, dev, planner)

analyze_db()