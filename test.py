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
import lab_bench.grendel_util as grendel_util
from enum import Enum

'''
The following functions turn a configured block
into a set_state command.
'''


ctx = llstructs.BuildContext()
# produce state object from array of codes

def build_profile(blk,loc,cfg,value_list,output):
  state_t = {blk.name:blk.state.concretize(cfg,loc)}
  loc_t = llstructs.make_block_loc(ctx,blk,loc)
  values = [0.0]*2
  for port,val in value_list:
    idx = port.to_code()
    assert(idx < 2)
    values[idx] = val

  profile_data = {"method": llenums.ProfileOpType.INPUT_OUTPUT.name, \
                  "inst": loc_t,
                  "in_vals": values, \
                  "state":state_t,
                  "output":output.name}

  cmd_data = llstructs.make_circ_cmd(ctx, \
                                     llenums.CircCmdType.PROFILE,
                                     profile_data)
  return ctx.build(cmd_data,debug=True)

def build_set_state(blk,loc,cfg):
  state_t = {blk.name:blk.state.concretize(cfg,loc)}
  loc_t = llstructs.make_block_loc(ctx,blk,loc)
  state_data = {'inst':loc_t, 'state':state_t}
  cmd_data = llstructs.make_circ_cmd(ctx, \
                                     llenums.CircCmdType.SET_STATE, \
                                     state_data)
  return ctx.build(cmd_data,debug=True)

def unpack_response(resp):
  if isinstance(resp,grendel_util.HeaderArduinoResponse):
    if resp.num_args == 1:
      return unpack_response(resp.data(0))
    elif resp.num_args == 0:
      return resp.msg
    else:
      raise Exception("only can handle responses with one or zero data segments")

  elif isinstance(resp,grendel_util.DataArduinoResponse):
    assert(isinstance(resp.value,grendel_util.PayloadArduinoResponse))
    return unpack_response(resp.value)

  elif isinstance(resp,grendel_util.PayloadArduinoResponse):
    payload_type = llstructs.parse(llstructs.response_type_t(), \
                                   bytes([resp.payload_type]))
    payload_result = None
    if payload_type == llenums.ResponseType.BLOCK_STATE.value:
      payload_result = llstructs.parse(llstructs.state_t(), \
                                       resp.values)
    elif payload_type == llenums.ResponseType.PROFILE_RESULT.value:
      payload_result = llstructs.parse(llstructs.profile_result_t(), \
                                       resp.array)

    return payload_result


# build an analog device program with one fanout block.
cfg = adplib.ADP()
loc = devlib.Location(None,[0,3,2,0])
cfg.add_instance(hwlib2.hcdc.fanout.fan,loc)
blkcfg = cfg.configs.get('fanout',loc)
blkcfg.modes = [['+','+','-','m']]

# get the fanout block specification from the hardware specification
fan_blk = hwlib2.hcdc.fanout.fan

# build the c struct for setting the state of the fanout block
state_t = build_set_state(fan_blk,loc,cfg)
print("-> built set_state command")

# build the c struct for profiling output 2 of the programmed fanout block
# when 1.2 is provided into input in0
profile_t = build_profile(fan_blk, \
                          loc, \
                          cfg, \
                          [(llenums.PortType.IN0, 1.2)], \
                          llenums.PortType.OUT2)

print("-> built profile command")

loc_t = llstructs.make_block_loc(ctx,hwlib2.hcdc.fanout.fan,loc)
data = llstructs.make_circ_cmd(ctx,llenums.CircCmdType.DISABLE, {'inst':loc_t})
disable_t = ctx.build(data,debug=True)
print("-> built disable_t command")

runtime = GrendelRunner()
print("<initialize>")
runtime.initialize()

print("<execute profile>")
runtime.execute(profile_t)
print("<result>")
resp = unpack_response(runtime.result())
print(resp)


print("<execute state>")
runtime.execute(state_t)
print("<result>")
print(runtime.result())

print("<execute state>")
runtime.execute(state_t)
print("<result>")
print(runtime.result())

print("<execute disable>")
runtime.execute(disable_t)
print("<result>")
print(runtime.result())


runtime.close()
