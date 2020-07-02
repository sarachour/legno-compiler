import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib
import itertools
import ops.op as oplib

from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum
import math
import numpy as np

import phys_model.profiler as proflib
import phys_model.planner as planlib
dev = hcdclib.get_device()
block = dev.get_block('mult')
inst = devlib.Location([0,1,2,0])
cfg = adplib.BlockConfig.make(block,inst)
#cfg.modes = [['+','+','-','m']]
cfg.modes = [block.modes.get(['x','m','m'])]
#cfg['pmos'].value = 0
#cfg['nmos'].value = 2
#cfg['bias_in0'].value = 31
#cfg['bias_in1'].value = 31
#cfg['bias_out'].value = 16

runtime = GrendelRunner()
runtime.initialize()
start = time.time()
proflib.calibrate(dev,runtime,block,inst,cfg)
end = time.time()
print("calibration time: %s" % (end-start))

#planner = planlib.SinglePointPlanner(block,inst,cfg,20)
#proflib.profile_all_hidden_states(runtime,dev,planner)
