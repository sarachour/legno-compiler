import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import phys_model.visualize as vizlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import time

def visualize_it(org):
  for key in org.keys():
    print("key: %s" % key)
    for codes,physblk in org.foreach(key):
      print(codes)
      vizlib.deviation(physblk,'output.png',amplitude=0.5)
      time.sleep(0.3)

    input("continue?")

dev = hcdclib.get_device()
block = dev.get_block('mult')
inst = devlib.Location([0,3,2,0])
cfg = adplib.BlockConfig.make(block,inst)
#cfg.modes = [['+','+','-','m']]
cfg.modes = [block.modes.get(['x','m','m'])]

db = physdb.PhysicalDatabase('board6')
org = physdb.HiddenCodeOrganizer(['pmos','nmos'])

for blk in physdb.get_all(db, dev):
  fitlib.analyze_physical_output(blk)
  org.add(blk)

#visualize_it(org)
