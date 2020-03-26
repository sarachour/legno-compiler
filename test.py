import hwlib2.hcdc.fanout
import hwlib2.hcdc.lut
import hwlib2.hcdc.dac
import hwlib2.hcdc.adc
import hwlib2.hcdc.mult

import hwlib2.device as devlib
import hwlib2.adp as adplib
import hwlib2.hcdc.llstructs as llstructs
import hwlib2.hcdc.llenums as llenums
from enum import Enum

'''
The following functions turn a configured block
into a set_state command.
'''


# produce state object from array of codes
def build_state_t(blk,loc,cfg):
  data = blk.codes.concretize(cfg,loc)
  return llstructs.validate(llstructs.state_t(),
                            {blk.name: data} \
  )

def build_set_state(blk,loc,cfg):
  state_t = build_state_t(blk,loc,cfg)
  loc_t = llstructs.build_block_loc(blk,loc)
  cmd_data = { 'inst':loc_t, 'state':state_t}
  cmd_type = llenums.CircCmdType.SET_STATE
  data = llstructs.build_circ_cmd(cmd_type,cmd_data)
  byts = llstructs.circ_cmd_t().build(data)
  print(byts)

cfg = adplib.ADP()
loc = devlib.Location(None,[0,3,2,0])
cfg.add_instance(hwlib2.hcdc.fanout.fan,loc)
blkcfg = cfg.configs.get('fanout',loc)
blkcfg.modes = [['+','+','-','m']]
state_t = build_set_state(hwlib2.hcdc.fanout.fan,loc,cfg)
print(state_t)
