import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import phys_model.visualize as vizlib
import hwlib.hcdc.hcdcv2 as hcdclib
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
import phys_model.lin_dectree as lindectree

dev = hcdclib.get_device()

def build_dataset():
  block,inst,cfg = targ.get_block(dev)

  db = physdb.PhysicalDatabase('board6')
  params = {}
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
    costs.append(blk.model.cost)

  return hidden_codes,inputs,params,costs

hidden_codes,inputs,params,costs = build_dataset()
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

errors = []
for pred,obs in zip(predictions,costs):
  print("%f %f" % (pred,obs))
  errors.append(abs(pred-obs))

print(dectree.pretty_print())
print("avg error: %f" % np.mean(errors))
print("error std: %f" % np.std(errors))
print("obs range: [%f,%f]" % (min(costs),max(costs)))

best_code = dict([('pmos', 0), ('nmos', 7), ('gain_cal', 31), ('bias_in0', 43), ('bias_in1', 50), ('bias_out', 8)])
print("best code pred:   %f" % dectree.evaluate(best_code))
print("best code actual: %f" % 0.010347767935215952)

default_bounds = {'pmos':[0,7],\
       'nmos':[0,7],\
       'gain_cal':[0,63],\
       'bias_out':[0,63],\
       'bias_in0':[0,63],\
       'bias_in1':[0,63],\
      }

dectree.update()
min_val,min_code = dectree.find_minimum(default_bounds)
print("\n\n",dectree.pretty_print(),"\n\n")
#print("\n\nmin_val is:%f" % min_val)
#print("min_val occurs at: ", min_code)
#print("leaves: ", dectree.leaves())
serialized_dectree_dict = {}
dectree.to_json(serialized_dectree_dict)
print("serialized_dectree: ", serialized_dectree_dict)

deserialized_dectree = lindectree.DecisionNode.from_json(serialized_dectree_dict)
print(deserialized_dectree.pretty_print())

print(dectree.random_sample())


