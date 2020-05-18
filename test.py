import hwlib2.hcdc.fanout
import hwlib2.hcdc.lut
import hwlib2.hcdc.dac
import hwlib2.hcdc.adc
import hwlib2.hcdc.mult

import hwlib2.device as devlib
import hwlib2.adp as adplib
import hwlib2.hcdc.llstructs as llstructs
import hwlib2.hcdc.llenums as llenums

from lab_bench.grendel_runner import GrendelRunner
from enum import Enum

'''
The following functions turn a configured block
into a set_state command.
'''


ctx = llstructs.BuildContext()
# produce state object from array of codes

def build_set_state(blk,loc,cfg):
  state_t = {blk.name:blk.codes.concretize(cfg,loc)}
  loc_t = llstructs.make_block_loc(ctx,blk,loc)
  state_data = {'inst':loc_t, 'state':state_t}
  cmd_data = llstructs.make_circ_cmd(ctx,llenums.CircCmdType.SET_STATE,state_data)
  return ctx.build(cmd_data,debug=True)


cfg = adplib.ADP()
loc = devlib.Location(None,[0,3,2,0])
cfg.add_instance(hwlib2.hcdc.fanout.fan,loc)
blkcfg = cfg.configs.get('fanout',loc)
blkcfg.modes = [['+','+','-','m']]
state_t = build_set_state(hwlib2.hcdc.fanout.fan,loc,cfg)
print("-> built set_state command")

loc_t = llstructs.make_block_loc(ctx,hwlib2.hcdc.fanout.fan,loc)
data = llstructs.make_circ_cmd(ctx,llenums.CircCmdType.DISABLE, {'inst':loc_t})
disable_t = ctx.build(data,debug=True)
print("-> built disable_t command")

runtime = GrendelRunner()
print("<initialize>")
runtime.initialize()

print("<execute state>")
print(state_t)
runtime.execute(state_t)
print("<result>")
runtime.result()

print("<execute state>")
runtime.execute(state_t)
print("<result>")
runtime.result()

print("<execute disable>")
runtime.execute(disable_t)
print("<result>")
runtime.result()


runtime.close()

