# running this script assumes the existence of a large dataset (~500+ hidden codes)
# stored in a file called board6.db, of the correct target block as specified in
# target_block.py

# code has been inherited from gather_dectree_data.py


#IMPORTS FROM GATHER_DECTREE_DATA.PY
import hwlib.hcdc.hcdcv2 as hcdclib
import phys_model.lin_dectree as lindectree
import target_block
import hwlib.physdb as physdb
from lab_bench.grendel_runner import GrendelRunner
import phys_model.profiler as proflib
import phys_model.planner as planlib
from analyze import analyze_db
import json



with open("static_dectree.json") as fh:
  serialized_dectree_dict = json.load(fh)

dectree = lindectree.DecisionNode.from_json(serialized_dectree_dict)
sample_list = dectree.random_sample()

dev = hcdclib.get_device()
block, inst, cfg = target_block.get_block(dev)
db = physdb.PhysicalDatabase('reparameterize_db')
runtime = GrendelRunner('reparameterize_db')

for current_sample_dict in sample_list:
	planner = planlib.SingleTargetedPointPlanner(block,inst,cfg,10,current_sample_dict)
	proflib.profile_all_hidden_states(runtime, dev, planner)

analyze_db('reparameterize_db')

#imports from no_refitting.py

import phys_model.model_fit as fitlib
import phys_model.visualize as vizlib

import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import ops.opparse as opparse
import ops.generic_op as genoplib
import target_block as targ
import ops.lambda_op as lambdoplib
import phys_model.region as reglib

import time
import matplotlib.pyplot as plt
import random
import time
import numpy as np
import phys_model.fit_lin_dectree as fit_lindectree



def build_dataset():
  block,inst,cfg = target_block.get_block(dev)

  db = physdb.PhysicalDatabase('reparameterize_db')
  params = {}
  param_A = []
  param_D = []
  inputs = []
  hidden_codes = []
  costs = []
  for blk in physdb.get_by_block_instance(db, dev,block,inst,cfg=cfg):
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

print("inputs:",inputs)
###
dectree,predictions = fit_lindectree.fit_decision_tree(hidden_codes, inputs,output, max_depth, min_size)

inputs_with_keys = {}

i = 0
for name in hidden_codes:
  inputs_with_keys[name] = inputs[:][i]
  i+=1 

index = 0
for name in hidden_codes:
  inputs_with_keys[name] = []
  for i in inputs:
    inputs_with_keys[name].append(i[index])
  index+=1


dataset = {}
dataset['meas_mean'] = costs
dataset['inputs'] = inputs_with_keys
output = dectree.fit(dataset)

serialized_dectree_dict = {}
dectree.to_json(serialized_dectree_dict)
with open("dynamic_dectree.json",'w') as fh:
  fh.write(json.dumps(serialized_dectree_dict))
