from enum import Enum
import hwlib.adp as adplib
import hwlib.block as blocklib
import hwlib.hcdc.llenums as llenums
import base64
import json

class PhysModelLabel(Enum):
  NONE = "none"


class DeltaModelLabel(Enum):
  MIN_ERROR = "min_error"
  MAX_FIT = "max_fit"
  LEGACY_MIN_ERROR = "legacy_min_error"
  LEGACY_MAX_FIT = "legacy_max_fit"
  NONE = "none"

  def from_calibration_objective(method,legacy=True):
    assert(isinstance(method,llenums.CalibrateObjective))
    if method == llenums.CalibrateObjective.MAXIMIZE_FIT:
      return (DeltaModelLabel.LEGACY_MAX_FIT if legacy \
        else DeltaModel.MAX_FIT)
    else:
      return (DeltaModelLabel.LEGACY_MIN_ERROR if legacy \
        else DeltaModel.MIN_ERROR)

def encode_dict(data):
  text = json.dumps(data)
  bytes_ = base64.b64encode(text.encode('utf-8')) \
                 .decode('utf-8')
  return bytes_

def decode_dict(data):
  text = base64.b64decode(data) \
               .decode('utf-8')
  return json.loads(text)

def dict_to_identifier(dict_):
  sorted_keys = sorted(dict_.keys())
  st = ""
  for k in sorted_keys:
    st += ";"
    st += "%s={%s}" % (k,dict_[k])

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
