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

from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum
import math
import numpy as np

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
planner = planlib.SensitivityPlanner(block,inst,cfg,32,10)
proflib.profile_all_hidden_states(runtime,dev,planner)

