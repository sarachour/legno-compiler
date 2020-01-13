import util.config as CFG
import util.util as util
import sqlite3
import json
import binascii
import math
import scipy
import numpy as np
import matplotlib.pyplot as plt


class PortModelError():

  def __init__(self):
    self._max = 0.0
    self._average = 0.0

  def copy():
    pe = PortModelError()

  @property
  def maximum(self):
    return self._max

  @property
  def average(self):
    return self._average


  def from_data(self,errors,values):
    n = len(errors)
    ival = max(map(lambda v: abs(v), values))
    pct_errors = list(map(lambda i : abs(errors[i])/ival,range(n)))
    self._average = np.mean(pct_errors)
    self._max = max(pct_errors)

  def to_json(self):
    return self.__dict__

  @staticmethod
  def from_json(obj):
    pe = PortModelError()
    pe.__dict__ = obj
    return pe

  def __repr__(self):
    return "{max=%f,avg=%f}" % (self.maximum, \
                                self.average)

class PortModel():

  def __init__(self,block,loc,port,comp_mode,scale_mode,calib_obj,handle=None):
    self._port = port
    self._block = block
    self._loc = loc
    self._handle = handle
    self._enabled = True
    self._gain = 1.0
    self._noise = 0.0
    self._bias = 0.0
    self._bias_uncertainty = PortModelError()
    self._gain_uncertainty = PortModelError()
    # the actual lower bound is [ospos*pos, osneg*neg]
    self._opscale = (1.0,1.0)
    self._comp_mode = util.normalize_mode(comp_mode)
    self._scale_mode = util.normalize_mode(scale_mode)
    self._calib_obj = calib_obj

  @staticmethod
  def from_json(obj):
    m = PortModel(None,None,None,None,None,None)
    m.__dict__ = obj
    m._comp_mode = util.normalize_mode(m._comp_mode)
    m._scale_mode = util.normalize_mode(m._scale_mode)
    m._calib_obj = util.CalibrateObjective(m._calib_obj)
    m._bias_uncertainty = PortModelError.from_json(obj['_bias_uncertainty'])
    m._gain_uncertainty = PortModelError.from_json(obj['_gain_uncertainty'])
    return m

  def to_json(self):
    jsn = dict(self.__dict__)
    jsn['_calib_obj'] = jsn['_calib_obj'].value
    jsn['_bias_uncertainty'] = jsn['_bias_uncertainty'].to_json()
    jsn['_gain_uncertainty'] = jsn['_gain_uncertainty'].to_json()
    return jsn

  def set_model(self,other):
    self._gain = other._gain
    self._enabled = other._enabled
    self._gain_uncertainty = other.gain_uncertainty.copy()
    self._bias_uncertainty = other.bias_uncertainty.copy()
    self._disable = other._disable
    self._noise = other._noise
    self._bias = other._bias
    l,u = self._opscale
    self._opscale = (l,u)

  @property
  def enabled(self):
    return self._enabled

  @enabled.setter
  def enabled(self,v):
    assert(isinstance(v,bool))
    self._enabled = v

  @property
  def gain(self):
    return self._gain

  @gain.setter
  def gain(self,v):
    assert(v > 0.0)
    self._gain = v

  @property
  def oprange_scale(self):
    return self._opscale

  def set_oprange_scale(self,a,b):
    assert(a >= 0)
    assert(b >= 0)
    self._opscale = (a,b)

  @property
  def identifier(self):
    ident = "%s-%s-%s-%s-%s-%s" % (self.block,self.loc,self.port,
                                   self.comp_mode,
                                   self.scale_mode,
                                   self.handle)
    return ident


  @property
  def comp_mode(self):
    return self._comp_mode

  @property
  def calib_obj(self):
    return self._calib_obj

  @property
  def scale_mode(self):
    return self._scale_mode

  @property
  def bias_uncertainty(self):
    return self._bias_uncertainty


  @property
  def gain_uncertainty(self):
    return self._gain_uncertainty


  @property
  def handle(self):
    return self._handle


  @property
  def block(self):
    return self._block

  @property
  def loc(self):
    return self._loc

  @property
  def port(self):
    return self._port

  @property
  def bias(self):
    return self._bias

  @bias.setter
  def bias(self,v):
    self._bias = v


  @property
  def noise(self):
    return self._noise


  @noise.setter
  def noise(self,v):
    assert(v >= 0.0)
    self._noise = v

  def __repr__(self):
    r = "=== model [%s] ===\n" % ("ON" if self.enabled else "OFF")
    r += "ident: %s\n" % (self.identifier)
    r += "bias: mean=%f std=%s\n" % (self.bias,self.bias_uncertainty)
    r += "gain: mean=%f std=%s\n" % (self.gain,self.gain_uncertainty)
    r += "noise: std=%f\n" % (self.noise)
    l,u = self._opscale
    r += ("scale=(%fx,%fx)\n" % (l,u))
    return r


class ModelDB:

  MISSING = []
  def __init__(self,calib_obj=util.CalibrateObjective.MIN_ERROR):
    self._conn = sqlite3.connect(CFG.MODEL_DB)
    self._curs = self._conn.cursor()
    self.calib_obj = calib_obj
    self._ignore = []
    cmd = '''
    CREATE TABLE IF NOT EXISTS models (
    calib_obj text NOT NULL,
    block text NOT NULL,
    loc text NOT NULL,
    port text NOT NULL,
    comp_mode text NOT NULL,
    scale_mode text NOT NULL,
    handle text NOT NULL,
    model text NOT NULL,
    PRIMARY KEY (calib_obj,block,loc,port,comp_mode,scale_mode,handle)
    )
    '''
    self._curs.execute(cmd)
    self._conn.commit()
    self.keys = ['calib_obj',
                 'block',
                 'loc',
                 'port',
                 'comp_mode',
                 'scale_mode',
                 'handle',
                 'model']


  def add_ignore(self,block):
    self._ignore.append(block)

  def ignore(self,block):
    return block in self._ignore

  @staticmethod
  def log_missing_model(block_name,loc,port,comp_mode,scale_mode):
    ModelDB.MISSING.append((block_name,loc,port,comp_mode,scale_mode))

  def get_all(self):
    cmd = '''
    SELECT * from models WHERE calib_obj = "{calib_obj}"
    '''.format(
      calib_obj=self.calib_obj.value \
    )
    for values in self._curs.execute(cmd):
      data = dict(zip(self.keys,values))
      yield self._process(data)

  def _process(self,data):
    obj = json.loads(bytes.fromhex(data['model']) \
                             .decode('utf-8'))

    model = PortModel.from_json(obj)
    return model


  def get_by_calibrate_objective(self):
    model = PortModel(block,loc,"",comp_mode,scale_mode,None)
    cmd = '''
    SELECT * from models WHERE
    calib_obj = "{calib_obj}"
    AND block = "{block}"
    AND loc = "{loc}"
    AND comp_mode = "{comp_mode}"
    AND scale_mode = "{scale_mode}"
    '''.format(
      calib_obj=self.calib_obj.value,
      block=model.block,
      loc=str(model.loc),
      comp_mode=str(model.comp_mode),
      scale_mode=str(model.scale_mode),
    )
    for values in self._curs.execute(cmd):
      data = dict(zip(self.keys,values))
      yield self._process(data)


  def get_by_block(self,block,loc,comp_mode,scale_mode):
    model = PortModel(block,loc,"",comp_mode,scale_mode,None)
    cmd = '''
    SELECT * from models WHERE
    calib_obj = "{calib_obj}"
    AND block = "{block}"
    AND loc = "{loc}"
    AND comp_mode = "{comp_mode}"
    AND scale_mode = "{scale_mode}"
    '''.format(
      calib_obj=self.calib_obj.value,
      block=model.block,
      loc=str(model.loc),
      comp_mode=str(model.comp_mode),
      scale_mode=str(model.scale_mode),
    )
    for values in self._curs.execute(cmd):
      data = dict(zip(self.keys,values))
      yield self._process(data)


  def _where_clause(self,block,loc,port,comp_mode,scale_mode,handle=None):
    cmd = '''
    WHERE calib_obj="{calib_obj}"
      AND block="{block}"
      AND loc="{loc}"
      AND port="{port}"
      AND comp_mode="{comp_mode}"
      AND scale_mode="{scale_mode}"
      AND handle="{handle}"
    '''.format(calib_obj=self.calib_obj.value, \
               block=block, \
               loc=str(loc), \
               port=str(port), \
               comp_mode=str(comp_mode), \
               scale_mode=str(scale_mode), \
               handle=handle)
    return cmd

  def _get(self,block,loc,port,comp_mode,scale_mode,handle=None):
    model = PortModel(block,loc,port,comp_mode,scale_mode,handle)
    cmd = '''
    SELECT * from models {where_clause};
    '''.format(
      where_clause=self._where_clause(block,loc,port, \
                                      comp_mode, \
                                      scale_mode, \
                                      handle))

    for values in self._curs.execute(cmd):
      data = dict(zip(self.keys,values))
      model = self._process(data)
      return model

    return None

  def get(self,block,loc,port,comp_mode,scale_mode,handle):
    return self._get(block,loc,port, \
                     comp_mode,scale_mode,handle)

  def has(self,block,loc,port,comp_mode,scale_mode,handle):
    return not self._get(block,loc,port, \
                         comp_mode,scale_mode,handle) is None

  def remove(self,block,loc,port,comp_mode,scale_mode,handle=None):
    model = PortModel(block,loc,port,comp_mode,scale_mode,handle)
    cmd = '''
    DELETE FROM models {where_clause};
    '''.format(
      where_clause=self._where_clause(block,loc,port, \
                                      comp_mode, \
                                      scale_mode, \
                                      handle))

    self._curs.execute(cmd)
    self._conn.commit()

  def put(self,model):
    model_bits = bytes(json.dumps(model.to_json()),'utf-8').hex()
    cmd =  '''
    INSERT INTO models (calib_obj,block,loc,port,comp_mode,scale_mode,handle,model)
    VALUES ("{calib_obj}","{block}","{loc}","{port}","{comp_mode}",
            "{scale_mode}","{handle}","{model}");
    '''.format(
      calib_obj=self.calib_obj.value,
      block=model.block,
      loc=str(model.loc),
      port=str(model.port),
      comp_mode=str(model.comp_mode),
      scale_mode=str(model.scale_mode),
      handle=str(model.handle),
      model=model_bits

    )
    self.remove(model.block,model.loc,model.port, \
                model.comp_mode,model.scale_mode,model.handle)
    assert(not self.has(model.block,model.loc,model.port, \
                        model.comp_mode,model.scale_mode,model.handle))
    self._curs.execute(cmd)
    self._conn.commit()



def get_model(db,circ,block_name,loc,port,handle=None):
    block = circ.board.block(block_name)
    config = circ.config(block_name,loc)
    if db.has(block.name,loc,port, \
              config.comp_mode, \
              config.scale_mode, \
              handle):
      model = db.get(block.name,loc,port, \
                     config.comp_mode, \
                     config.scale_mode,handle)
      return model
    else:
      assert(not config.scale_mode is None and \
             not config.scale_mode == "None")
      ModelDB.log_missing_model(block_name,loc,port, \
                                config.comp_mode,
                                config.scale_mode)
      #print("no model: %s[%s].%s :%s cm=%s scm=%s" % \
      #      (block_name,loc,port,handle, \
      #       str(config.comp_mode), \
      #       str(config.scale_mode)))
      return None

def get_ideal_uncertainty(circ,block_name,loc,port,handle=None):
  blacklist = ['tile_in','tile_out', \
               'chip_in','chip_out', \
               'ext_chip_out', \
               'ext_chip_in'
  ]
  base_unc = 0.01
  if block_name in blacklist:
    return base_unc

  cfg = circ.config(block_name,loc)
  block = circ.board.block(block_name)
  props = block.props(cfg.comp_mode,cfg.scale_mode,port,handle=handle)
  rng= props.interval().spread
  unc = rng/2.0*base_unc;
  #unc = base_unc
  return unc

def get_variance(db,circ,block_name,loc,port,mode,handle=None):

  if mode == util.DeltaModel.IDEAL:
    return 1e-12

  elif mode.uses_delta_model():
    model = get_model(db,circ,block_name,loc,port,handle=handle)
    if model is None or not mode.uses_uncertainty():
      return get_ideal_uncertainty(circ,block_name,loc,port,handle=handle)

    unc = math.sqrt(model.noise + model.bias_uncertainty.maximum**2.0)
    physunc = unc+abs(model.bias)
    if physunc == 0.0:
      return 1e-12

    return physunc

  else:
    return get_ideal_uncertainty(circ,block_name,loc,port,handle=handle)

def get_oprange_scale(db,circ,block_name,loc,port,mode,handle=None):
  assert(isinstance(mode,util.DeltaModel))
  if mode.uses_delta_model():
    model = get_model(db,circ,block_name,loc,port,handle=handle)
    if model is None or db.ignore(block_name):
      return (1.0,1.0)

    l,u = model.oprange_scale
    #print(l,u)
    #input()
    return (l,u)

  else:
    return (1.0,1.0)


def get_bias(db,circ,block_name,loc,port,mode,handle=None):
  assert(isinstance(mode,util.DeltaModel))
  if mode.uses_delta_model():
    model = get_model(db,circ,block_name,loc,port,handle=handle)
    if model is None  or db.ignore(block_name):
      return 0.0

    return model.bias

  else:
    return 0.0


def get_gain(db,circ,block_name,loc,port,mode,handle=None):
  assert(isinstance(mode,util.DeltaModel))
  if mode.uses_delta_model():
    model = get_model(db,circ,block_name,loc,port,handle=handle)
    if model is None or db.ignore(block_name):
      return 1.0

    return model.gain

  else:
    return 1.0
