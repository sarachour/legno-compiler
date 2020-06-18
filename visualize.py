import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import json

import ops.lambda_op as lambdoplib

dev = hcdclib.get_device()
block = dev.get_block('mult')
inst = devlib.Location([0,3,2,0])


db = physdb.PhysicalDatabase('board6')
dataset = {}
for blk in physdb.get_all_configured_calibrated_blocks(db, \
                                                       dev,block, \
                                                       inst):
  if not blk.static_cfg in dataset:
    dataset[blk.static_cfg] = {}

  entry = blk.to_json()
  if blk.model.complete:
    data = blk.dataset.get_data(llenums.ProfileStatus.SUCCESS, \
                                llenums.ProfileOpType.INPUT_OUTPUT)
    pred_model = blk.model.predict(data['inputs'])
    pred_delta = blk.model.predict(data['inputs'], \
                                   correctable_only=True)
    del entry['dataset']
    entry['data'] = data
    entry['data']['predict'] = pred_model
    entry['data']['delta_model'] = pred_delta
    entry['info'] = {}

    variables,strrepr = lambdoplib.to_python(blk.model.delta_model.get_model(blk.model.params))
    entry['info']['model'] = strrepr

    variables,strrepr = lambdoplib.to_python(blk.model.delta_model.get_correctable_model(blk.model.params))
    entry['info']['correctable_model'] = strrepr

    entry['bounds'] = blk.get_bounds()
    dataset[blk.static_cfg][blk.hidden_cfg] = entry

with open('output.json','w') as fh:
  fh.write(json.dumps(dataset))
