import hwlib2.device as devlib
import hwlib2.adp as adplib
import hwlib2.hcdc.llstructs as llstructs
import hwlib2.hcdc.hcdcv2 as hcdclib
import hwlib2.hcdc.llenums as llenums
import hwlib2.physdb as physdb

import lab_bench.grendel_util as grendel_util


def from_block_loc_t(dict_):
    dev = hcdclib.get_device()
    chip = dict_['chip']
    tile = dict_['tile']
    slice_ = dict_['slice']
    idx = dict_['idx']
    block_type = llenums.BlockType.by_name(str(dict_['block']))
    blk = dev.get_block(block_type.value)
    addr = [int(dict_['chip']), \
            int(dict_['tile']), \
            int(dict_['slice']), \
            int(dict_['idx'])]
    return blk,devlib.Location(addr)

def make_block_loc_t(blk,loc):
  assert(len(loc) == 4)
  addr = loc.address
  loc = {
    'block':llenums.BlockType(blk.name).name,
    'chip':addr[0],
    'tile':addr[1],
    'slice':addr[2],
    'idx':addr[3]
  }
  return llstructs.block_loc_t(),loc

def make_port_loc(blk,loc,port):
  assert(isinstance(ctx,BuildContext))
  assert(len(loc) == 4)
  loc = { \
          'inst':build_block_loc(blk,loc), \
          'port':PortType(port).name}

  return port_loc_t(),loc


def make_circ_cmd(cmdtype,cmddata):
    assert(isinstance(cmdtype,llenums.CircCmdType))
    cmd_d = {
        "cmd_type": llenums.CmdType.CIRC_CMD.name,
        "cmd_data":{
            "circ_cmd": {
                'circ_cmd_type': cmdtype.name,
                'circ_cmd_data': {cmdtype.value:cmddata}
            }
        }
    }
    return llstructs.cmd_t(),cmd_d

def _unpack_response(resp):
  if isinstance(resp,grendel_util.HeaderArduinoResponse):
    if resp.num_args == 1:
      return _unpack_response(resp.data(0))
    elif resp.num_args == 0:
      return resp.message
    else:
      raise Exception("only can handle responses with one or zero data segments")

  elif isinstance(resp,grendel_util.DataArduinoResponse):
    assert(isinstance(resp.value,grendel_util.PayloadArduinoResponse))
    return _unpack_response(resp.value)

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


def profile(runtime,blk,loc,cfg,output_port,in0=0.0,in1=0.0):
    state_t = {blk.name:blk.state.concretize(cfg,loc)}
    # build command
    loc_t,loc_d = make_block_loc_t(blk,loc)
    values = [0.0]*2
    values[llenums.PortType.IN0.code()] = in0
    values[llenums.PortType.IN1.code()] = in1
    profile_data = {"method": llenums.ProfileOpType.INPUT_OUTPUT.name, \
                    "inst": loc_d,
                    "in_vals": values, \
                    "state":state_t,
                    "output":output_port.name}

    cmd_t, cmd_data = make_circ_cmd(llenums.CircCmdType.PROFILE,
                             profile_data)
    cmd = cmd_t.build(cmd_data,debug=True)

    # execute command
    runtime.execute(cmd)
    resp = _unpack_response(runtime.result())

    # reconstruct analog device program
    new_adp= adplib.ADP()
    blk,loc = from_block_loc_t(resp['spec']['inst'])
    new_adp.add_instance(blk,loc)
    state = resp['spec']['state'][blk.name]
    blk.state.lift(new_adp,loc,dict(state))

    # retrieve parametesr for new result
    new_in0 = resp['spec']['in_vals'][llenums.PortType.IN0.code()]
    new_in1 = resp['spec']['in_vals'][llenums.PortType.IN1.code()]
    new_out = llenums.PortType.from_code(int(resp['spec']['output']))
    new_method = resp['spec']['method']
    out_mean = resp['mean']
    out_std = resp['stdev']
    out_status = resp['status']

    # insert into database
    print("TODO: fix status. It's unknown")
    assert(isinstance(new_out,llenums.PortType))
    blkcfg = new_adp.configs.get(blk.name,loc)
    db = physdb.PhysicalDatabase(runtime.board_name)
    db.get(blk,loc,new_out,blkcfg) \
      .add_datapoint(in0=new_in0, \
                     in1=new_in1, \
                     out_port=new_out, \
                     method = new_method, \
                     mean=out_mean, \
                     std=out_std)

    return blkcfg

def set_state(runtime,blk,loc,cfg):
    state_t = {blk.name:blk.state.concretize(cfg,loc)}
    loc_t,loc_d = make_block_loc_t(blk,loc)
    state_data = {'inst':loc_d, 'state':state_t}
    cmd_t,cmd_data = make_circ_cmd(llenums.CircCmdType.SET_STATE, \
                                       state_data)
    cmd = cmd_t.build(cmd_data,debug=True)
    runtime.execute(cmd)
    return _unpack_response(runtime.result())

def disable(runtime,blk,loc):
    loc_t,loc_d = make_block_loc_t(blk,loc)
    cmd_t,cmd_d = make_circ_cmd(llenums.CircCmdType.DISABLE,  \
                                          {'inst':loc_d})
    cmd = cmd_t.build(cmd_d,debug=True)
    runtime.execute(cmd)
    return _unpack_response(runtime.result())
