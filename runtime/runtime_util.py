import dslang.dsprog as dsproglib

import hwlib.hcdc.llenums as llenums
import hwlib.block as blocklib
import hwlib.adp as adplib

import ops.op as oplib
import ops.generic_op as genoplib
import ops.interval as ivallib

import compiler.lscale_pass.lscale_widening as widenlib
import json
import numpy as np
import base64
import math

def make_block_test_adp(board,adp,block,cfg):
  if block.name == "dac" and 'dyn' in str(cfg.mode):
    lut_blk = board.get_block('lut')
    dac_loc = cfg.inst.loc
    lut0_loc,lut1_loc = cfg.inst.loc.copy(), cfg.inst.loc.copy()
    lut1_loc[2] = 0 if dac_loc[2] == 2 else 2

    lut_out = list(lut_blk.outputs)[0]
    dac_in = list(block.inputs)[0]

    adp_lut0 = adp.copy(board)
    adp_lut0.add_instance(lut_blk,lut0_loc)
    adp_lut0.add_conn(lut_blk, lut0_loc, lut_out, \
                      block, dac_loc, dac_in)
    return adp_lut0

  else:
    return adp


def get_profiling_steps(output_port,cfg,grid_size,max_points=None):

    if is_integration_op(output_port.relation[cfg.mode]):
      if not max_points is None and  max_points < grid_size:
        grid_size = max_points

      yield llenums.ProfileOpType.INTEG_DERIVATIVE_BIAS,0,0,3
      yield llenums.ProfileOpType.INTEG_DERIVATIVE_GAIN,0,0,3
      yield llenums.ProfileOpType.INTEG_DERIVATIVE_STABLE,0,0,3
      yield llenums.ProfileOpType.INTEG_INITIAL_COND,grid_size,1,1

    elif cfg.inst.block == "mult":
      if not max_points is None and  max_points < grid_size*grid_size:
        grid_size = round(math.sqrt(max_points))

      yield llenums.ProfileOpType.INPUT_OUTPUT,grid_size,grid_size,1
    else:
      if not max_points is None and max_points < grid_size:
        grid_size = max_points

      yield llenums.ProfileOpType.INPUT_OUTPUT,grid_size,1,1



def get_adp(board,filename,widen=True):
    with open(filename,'r') as fh:
        adp = adplib.ADP.from_json(board, \
                            json.loads(fh.read()))
        if widen:
            for cfg in adp.configs:
                blk = board.get_block(cfg.inst.block)
                cfg.modes = widenlib.widen_modes(blk,
                                                cfg)

        return adp

def encode_dict(data):
  text = json.dumps(data)
  bytes_ = base64.b64encode(text.encode('utf-8')) \
                 .decode('utf-8')
  return bytes_

def decode_dict(data):
  text = base64.b64decode(data) \
               .decode('utf-8')
  return json.loads(text)

def is_integration_op(rel):
    for node in rel.nodes():
        if node.op == oplib.OpType.INTEG:
            return True
    return False


def dict_to_identifier(dict_):
  sorted_keys = sorted(dict_.keys())
  st = ""
  for k in sorted_keys:
    st += ";"
    st += "%s=%s" % (k,dict_[k])

  return "[" + st[1:] + "]"


def get_hidden_cfg(block,cfg,exclude=[]):
    mode = cfg.mode
    kvs = {}
    for stmt in cfg.stmts:
      if stmt.type == adplib.ConfigStmtType.STATE and \
         isinstance(block.state[stmt.name].impl, \
                        blocklib.BCCalibImpl) and \
                        not stmt.name in exclude:
        assert(not stmt.name in kvs)
        kvs[stmt.name] = stmt.type.value+" "+stmt.pretty_print()

    return dict_to_identifier(kvs)

def get_static_cfg(block,cfg):
    mode = cfg.mode
    kvs = {}
    kvs['mode'] = mode
    for stmt in cfg.stmts:
      if stmt.type == adplib.ConfigStmtType.STATE and \
         not isinstance(block.state[stmt.name].impl, \
                        blocklib.BCCalibImpl):
        assert(not stmt.name in kvs)
        kvs[stmt.name] = stmt.t.value+" "+stmt.pretty_print()

    return dict_to_identifier(kvs)

def get_dynamic_cfg(cfg):
    kvs = {}
    for stmt in cfg.stmts:
      if stmt.type == adplib.ConfigStmtType.CONSTANT:
        assert(not stmt.name in kvs)
        kvs[stmt.name] = stmt.value
    return kvs

def get_device(model_no,layout=False):
    assert(not model_no is None)
    import hwlib.hcdc.hcdcv2 as hcdclib
    return hcdclib.get_device(model_no,layout=layout)


def select_from_array(arr,n):
  space = math.ceil(len(arr)/n)
  subarr = arr[0:len(arr):space]
  return subarr

def select_from_interval(ival,n):
  return list(np.linspace(ival.lower,ival.upper,n))

def select_from_quantized_interval(ival,quant,n):
  values = quant.get_values(ival)
  return select_from_array(values,n)


def get_subarray(arr,inds):
  return list(map(lambda i: arr[i], inds))
