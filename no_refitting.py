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
import json

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

print("inputs:",inputs)
###
dectree,predictions = fit_lindectree.fit_decision_tree(hidden_codes, inputs,output, max_depth, min_size)

serialized_dectree_dict = {}
dectree.to_json(serialized_dectree_dict)
dectree = lindectree.DecisionNode.from_json(serialized_dectree_dict)

with open("predictions.json",'w') as fh:
  fh.write(json.dumps(predictions))

with open("dectree.json",'w') as fh:
  fh.write(json.dumps(serialized_dectree_dict))


###
with open("dectree.json") as fh:
  serialized_dectree_dict = json.load(fh)

dectree = lindectree.DecisionNode.from_json(serialized_dectree_dict)

with open("predictions.json") as fh:
  predictions = json.load(fh)

errors = []
for pred,obs in zip(predictions,costs):
  print("%f %f" % (pred,obs))
  errors.append(abs(pred-obs))

#print(dectree.pretty_print())
#print("avg error: %f" % np.mean(errors))
#print("error std: %f" % np.std(errors))
#print("obs range: [%f,%f]" % (min(costs),max(costs)))

best_code = dict([('pmos', 0), ('nmos', 7), ('gain_cal', 31), ('bias_in0', 43), ('bias_in1', 50), ('bias_out', 8)])
#print("best code pred:   %f" % dectree.evaluate(best_code))
#print("best code actual: %f" % 0.010347767935215952)

default_bounds = {'pmos':[0,7],\
       'nmos':[0,7],\
       'gain_cal':[0,63],\
       'bias_out':[0,63],\
       'bias_in0':[0,63],\
       'bias_in1':[0,63],\
      }

dectree.update()
min_val,min_code = dectree.find_minimum(default_bounds)
#print("\n\n",dectree.pretty_print(),"\n\n")
#print("\n\nmin_val is:%f" % min_val)
#print("min_val occurs at: ", min_code)
#print("leaves: ", dectree.leaves())
#serialized_dectree_dict = {}
#dectree.to_json(serialized_dectree_dict)

#with open("predictions.json",'w') as fh:
#  fh.write(json.dumps(predictions))

#with open("dectree.json",'w') as fh:
#  fh.write(json.dumps(serialized_dectree_dict))



#print("serialized_dectree: ", serialized_dectree_dict)

#deserialized_dectree = lindectree.DecisionNode.from_json(serialized_dectree_dict)
#print(deserialized_dectree.pretty_print())

#print(dectree.random_sample())

#print("\n\n\nHIDDEN CODES:",hidden_codes,"\n\n\n")
#print("\n\n\nCOSTS:",costs,"\n\n\n")
#print("\n\n\nINPUTS:",inputs,"\n\n\n")
#print("\n\n\nPARAMS:",params,"\n\n\n")

#print("\n\n\nlen(HIDDEN CODES):",len(hidden_codes),"\n\n\n")
#print("\n\n\nlen(COSTS):",len(costs),"\n\n\n")
#print("\n\n\nlen(INPUTS):",len(inputs),"\n\n\n")
#print("\n\n\nlen(PARAMS['a']):",len(params['a']),"\n\n\n")
inputs_with_keys = {}
'''
for input_code in inputs:
  input_dict = {}
  i = 0
  for name in hidden_codes:
    input_dict[name] = input_code[i]
    i+=1
  inputs_with_keys.append(input_dict)
'''
i = 0
for name in hidden_codes:
  inputs_with_keys[name] = inputs[:][i]
  i+=1 


'''want: {'pmos':[0,3,1,4,1,2], 'nmos':[0,2,5,3,24,]......}
have hidden_codes = [pmos, nmos]

inputs = [[0,1,2,3,4,5],[,6,7,8,9,1,3],[]]
'''
index = 0
for name in hidden_codes:
  inputs_with_keys[name] = []
  for i in inputs:
    inputs_with_keys[name].append(i[index])
  index+=1

dataset = {}
dataset['meas_mean'] = costs
dataset['inputs'] = inputs_with_keys
#print("CRAFTED DATASET IS:", dataset)
output = dectree.fit(dataset)

print(dectree.min_sample())
