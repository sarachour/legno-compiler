import hwlib2.hcdc.fanout
import hwlib2.hcdc.lut
import hwlib2.hcdc.dac
import hwlib2.hcdc.adc
import hwlib2.hcdc.mult

import hwlib2.device as devlib
import hwlib2.adp as adplib
import hwlib2.hcdc.llstructs as llstructs
import hwlib2.hcdc.llenums as llenums
import hwlib2.hcdc.llcmd as llcmd

from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum

'''
The following functions turn a configured block
into a set_state command.
'''

loc = devlib.Location([0,3,2,0])
blk = hwlib2.hcdc.fanout.fan

cfg = adplib.ADP()
cfg.add_instance(blk,loc)
blkcfg = cfg.configs.get(blk.name,loc)
blkcfg.modes = [['+','+','-','m']]

runtime = GrendelRunner()
runtime.initialize()

#llcmd.set_state(runtime,blk,loc,cfg)

result = llcmd.profile(runtime,blk,loc,cfg, \
                       output_port=llenums.PortType.OUT2, \
                       in0=1.2)
print(result)


#llcmd.set_state(runtime,blk,loc,cfg)
#llcmd.disable(runtime,blk,loc)

runtime.close()
