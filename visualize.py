
import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import phys_model.visualize as vizlib
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import json
import target_block
import ops.lambda_op as lambdoplib

dev = hcdclib.get_device()
block,inst,cfg = target_block.get_block(dev)

db = physdb.PhysicalDatabase('board6')
params = {}
inputs = {}
costs = []
for blk in physdb.get_by_block_instance(db, dev,block,inst,cfg=cfg):
  for par,value in blk.model.params.items():
    if not par in params:
      params[par] = []
    params[par].append(value)


  for hidden_code,value in blk.hidden_codes():
    if not hidden_code in inputs:
      inputs[hidden_code] = []
    inputs[hidden_code].append(value)

  vizlib.deviation(blk,'output.png', \
                   num_bins=32, \
                   baseline=vizlib.ReferenceType.MODEL_PREDICTION, \
                   relative=True)
  costs.append(blk.model.cost)


