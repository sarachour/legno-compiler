import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import phys_model.visualize as vizlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import ops.opparse as opparse
import time
import target_block

def analyze_db():
	dev = hcdclib.get_device()
	block,inst,cfg = target_block.get_block(dev)

	db = physdb.PhysicalDatabase('board6')
	# build up dataset
	params = {}
	inputs = {}
	for blk in physdb.get_by_block_instance(db, dev,block,inst,cfg=cfg):
  		fitlib.analyze_physical_output(blk)
	return

dev = hcdclib.get_device()
block,inst,cfg = target_block.get_block(dev)

db = physdb.PhysicalDatabase('board6')
# build up dataset
params = {}
inputs = {}
for blk in physdb.get_by_block_instance(db, dev,block,inst,cfg=cfg):
  	fitlib.analyze_physical_output(blk)