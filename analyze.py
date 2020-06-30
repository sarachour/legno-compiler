import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import phys_model.visualize as vizlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import ops.opparse as opparse
import time

dev = hcdclib.get_device()
block = dev.get_block('mult')
inst = devlib.Location([0,1,2,0])
cfg = adplib.BlockConfig.make(block,inst)
#cfg.modes = [['+','+','-','m']]
cfg.modes = [block.modes.get(['x','m','m'])]

db = physdb.PhysicalDatabase('board6')
# build up dataset
params = {}
inputs = {}
for blk in physdb.get_by_block_instance(db, dev,block,inst,cfg=cfg):
  fitlib.analyze_physical_output(blk)
