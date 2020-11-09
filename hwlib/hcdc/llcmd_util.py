import hwlib.block as blocklib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llstructs as llstructs
import util.paths as pathlib
import hwlib.physdb as physlib

import lab_bench.grendel_util as grendel_util

def open_physical_db(board):
    if board.physdb is None:
        board.physdb = physlib.PhysicalDatabase(board.name, \
                                                  pathlib.PathHandler.DEVICE_STATE_DIR)

def get_by_ll_identifier(collection,ident):
    for port in collection:
        if port.ll_identifier == ident:
            return port


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
  assert(isinstance(blk,blocklib.Block))

  addr = loc.address
  loc = {
    'block':llenums.BlockType(blk.ll_name).name,
    'chip':addr[0],
    'tile':addr[1],
    'slice':addr[2],
    'idx':addr[3]
  }
  return llstructs.block_loc_t(),loc

def make_port_loc(blk,loc,port):
  assert(len(loc) == 4)
  assert(isinstance(blk,blocklib.Block))
  addr = loc.address
  loc = {
    'block':llenums.BlockType(blk.ll_name).name,
    'chip':addr[0],
    'tile':addr[1],
    'slice':addr[2],
    'idx':addr[3]
  }
  loc = { \
          'loc':loc, \
          'port':llenums.PortType(port).name}

  return llstructs.port_loc_t(),loc

def make_exp_cmd(cmdtype,args,flag):
    assert(isinstance(cmdtype,llenums.ExpCmdType))
    assert('ints' in args or 'floats' in args)
    cmd_d = {
        "cmd_type": llenums.CmdType.EXPERIMENT_CMD.name,
        "cmd_data":{
            "exper_cmd": {
                'type': cmdtype.name,
                'args': args,
                'flag': flag
            }
        }
    }
    return llstructs.cmd_t(),cmd_d


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

def unpack_response(resp):
  if isinstance(resp,grendel_util.HeaderArduinoResponse):
    if resp.num_args == 1:
      return unpack_response(resp.data(0))
    elif resp.num_args == 0:
      return resp.message
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
                                       resp.array)
    elif payload_type == llenums.ResponseType.PROFILE_RESULT.value:
      payload_result = llstructs.parse(llstructs.profile_result_t(), \
                                       resp.array)

    return payload_result
