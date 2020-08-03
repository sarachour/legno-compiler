import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib
import target_block
import itertools
import ops.op as oplib
from analyze import analyze_db
from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum
import math
import numpy as np
from fit_and_minimize import investigate_model
import phys_model.profiler as proflib
import phys_model.planner as planlib

'''
dev = hcdclib.get_device()
block = dev.get_block('integ')
inst = devlib.Location([0,3,2,0])
cfg = adplib.BlockConfig.make(block,inst)
cfg.modes = [block.modes.get(['m','m','+'])]
characterize(block,inst,cfg)
'''

#block = dev.get_block('fanout')
dev = hcdclib.get_device()
block,inst,cfg = target_block.get_block(dev)

runtime = GrendelRunner()
#planner = planlib.BruteForcePlanner(block,inst,cfg,3,10)
#planner = planlib.NeighborhoodPlanner(block,inst,cfg,3,10)
#planner = planlib.SensitivityPlanner(block,inst,cfg,32,10)
#planner = planlib.CorrelationPlanner(block,inst,cfg,8,10)
#planner = planlib.ModelBasedPlanner(block,inst,cfg,8,10)

planner = planlib.RandomPlanner(block,inst,cfg,8,10,25)
proflib.profile_all_hidden_states(runtime,dev,planner)
analyze_db()

for i in range(10):
	new_optimal_code = {}
	optimal_code = investigate_model("A")
	for name,value in optimal_code.items():
		new_optimal_code[block.state[name]] = value
	#for name,val in optimal_code.items():
		#cfg[name].value = val
	test_planner = planlib.SinglePointPlanner(block,inst,cfg,10)
	test_planner.new_hidden()
	proflib.profile_hidden_state(dev,runtime,test_planner,new_optimal_code)



'''
first test out 15 random hidden codes
then fit models of A, D, cost to the database generated by those hidden codes
minimize one of the models, for example cost
at the hidden code corresponding to cost,

'''


