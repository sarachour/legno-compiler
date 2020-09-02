# this is a combination of characterize.py and decision_tree_regress.py,
# aiming to simplify the process of building a new dectree, 
# including gathering a large dataset to determine the structure

# CHARACTERIZE.PY IMPORTS
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.physdb as physdb
import target_block as targ
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

#DECISION_TREE_REGRESS.PY IMPORTS
import phys_model.model_fit as fitlib
import phys_model.visualize as vizlib
import ops.opparse as opparse
import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
import phys_model.region as reglib
import phys_model.fit_lin_dectree as fit_lindectree
import phys_model.lin_dectree as lindectree

import time
import random
import numpy as np
import json

# this is the number of random samples that will be taken from the block 
# specified in target_block.py, to build the large initial dataset

NUM_SAMPLES = 1000

dev = hcdclib.get_device()
block, inst, cfg = targ.get_block(dev)
db = physdb.PhysicalDatabase('board6')
runtime = GrendelRunner()

planner = planlib.RandomPlanner(block, inst, cfg, 8, 10, 1000)
proflib.profile_all_hidden_states(runtime, dev, planner)
analyze_db()

# at this point in the code, board6.db is a large dataset of random samples,
# the next job is to fit a decision tree to this dataset, using code
# inherited from decision_tree_regress.py

def build_dataset():
  block,inst,cfg = targ.get_block(dev)

  db = physdb.PhysicalDatabase('board6')
  params = {}
  inputs = []
  hidden_codes = []
  costs = []
  param_A = []
  param_D = []
  for blk in physdb.get_by_block_instance(db,dev,block,inst,cfg=cfg):
    if not blk.model.complete:
      print("[WARN] found incomplete delta model")
      continue

    else:
      print("success")

    for par,value in blk.model.params.items():
      if not par in params:
        params[par] = []
      params[par].append(value)


    for hidden_code,value in blk.hidden_codes():
      if not hidden_code in hidden_codes:
        hidden_codes.append(hidden_code)

    entry = [0]*(len(hidden_codes))
    for hidden_code,value in blk.hidden_codes():
      idx = hidden_codes.index(hidden_code)
      entry[idx] = value

    inputs.append(entry)
    param_A.append(blk.model.params["a"])
    param_D.append(blk.model.params["d"])
    costs.append(blk.model.cost)

  return hidden_codes,inputs,params,costs,param_A,param_D

hidden_codes,inputs,params,costs,param_A,param_D = build_dataset()
np_inputs = np.array(inputs)
np_costs = np.array(costs)
n_samples = len(costs)
n_folds = 5
max_depth = 3
min_size = round(n_samples/20.0)
print("--- fitting decision tree (%d samples) ---" % n_samples)
output = costs
dectree,predictions = fit_lindectree.fit_decision_tree(hidden_codes, \
                                                       inputs,output, \
                                                       max_depth, \
                                                       min_size)

dectree.update() #is this required?

serialized_dectree_dict = {}
dectree.to_json(serialized_dectree_dict)
with open("static_dectree.json",'w') as fh:
  json.dump(serialized_dectree_dict, fh)