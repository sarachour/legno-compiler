import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib
import itertools
import ops.op as oplib
import time

from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum
import math
import numpy as np

import phys_model.profiler as proflib
import phys_model.planner as planlib
import target_block
import sys

def calibrate(dev,block,inst,cfg):
  runtime = GrendelRunner()
  runtime.initialize()
  start = time.time()
  proflib.calibrate(dev,runtime,block,inst,cfg)
  end = time.time()
  print("calibration time: %s" % (end-start))

def profile_calibrated(dev,block,inst,cfg):
  runtime = GrendelRunner()
  planner = planlib.SinglePointPlanner(block,inst,cfg,12)
  proflib.profile_all_hidden_states(runtime,dev,planner)


  cfg['nmos'].value = 7
  cfg['pmos'].value = 3
  cfg['gain_cal'].value = 63
  profile_calibrated(dev,block,inst,cfg)

do_calibrate = False
dev = hcdclib.get_device()
block,inst,cfg = target_block.get_block(dev)
if do_calibrate:
  calibrate(dev,block,inst,cfg)
else:
  profile_calibrated(dev,block,inst,cfg)
