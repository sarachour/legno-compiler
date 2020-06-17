import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import json

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
    prediction = blk.model.predict(data['inputs'])
    del entry['dataset']
    entry['data'] = data
    entry['data']['predict'] = prediction

  dataset[blk.static_cfg][blk.hidden_cfg] = blk.to_json()

with open('output.json','w') as fh:
  fh.write(json.dumps(dataset))
