import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib

dev = hcdclib.get_device()
block = dev.get_block('mult')
inst = devlib.Location([0,3,2,0])
cfg = adplib.BlockConfig.make(block,inst)
#cfg.modes = [['+','+','-','m']]
cfg.modes = [block.modes.get(['x','m','m'])]


db = physdb.PhysicalDatabase('board6')
for blk in physdb.get_all_calibrated_blocks(db,dev,block,inst,cfg):
  fitlib.analyze_physical_output(blk)

print("===== BEST CALIBRATION CODE ====")
for blk in physdb.get_best_calibrated_block(db,dev,block,inst,cfg):
  print(blk.hidden_cfg)
