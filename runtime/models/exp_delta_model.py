import hwlib.hcdc.llenums as llenums

import hwlib.block as blocklib
import hwlib.device as devlib
import hwlib.adp as adplib

import runtime.runtime_util as runtime_util
import runtime.models.database as dblib

import ops.generic_op as genoplib
import numpy as np

class ExpDeltaModel:
  MAX_MODEL_ERROR = 9999

  def __init__(self,blk,loc,output,cfg):
    assert(isinstance(blk,blocklib.Block))
    assert(isinstance(loc,devlib.Location))
    assert(isinstance(output,blocklib.BlockOutput))
    assert(isinstance(cfg,adplib.BlockConfig))

    self.block = blk
    self.loc = loc
    self.output = output
    self.config = cfg
    self._params = {}
    self._model_error = ExpDeltaModel.MAX_MODEL_ERROR
    self.calib_obj = llenums.CalibrateObjective.NONE

  @property
  def params(self):
    return dict(self._params)

  @property
  def spec(self):
    return self.output.deltas[self.config.mode]

  @property
  def model_error(self):
    return self._model_error

  @property
  def relation(self):
    return self.spec.relation

  @property
  def is_integration_op(self):
    rel = self.spec.get_model(self.params)
    return runtime_util.is_integration_op(rel)

  @property
  def complete(self):
    if self.spec is None:
      raise Exception("no delta spec: %s.%s %s" \
                      % (self.block.name, \
                         self.output.name, \
                         self.config.mode))

    for par in self.spec.params:
      if not par in self._params:
        return False
    return True

  def clear(self):
    self.params = {}
    self.model_error = ExpDeltaModel.MAX_MODEL_ERROR

  def bind(self,par,value):
    assert(not par in self._params)
    if not (par in self.spec.params):
      print("WARN: couldn't bind nonexistant parameter <%s> in delta" % par)
      return

    self._params[par] = value

  def set_model_error(self,error):
    self._model_error = error

  def error(self,dataset,init_cond=False,correctable_only=False):
    predictions = self.predict(dataset, \
                               init_cond=init_cond, \
                               correctable_only=correctable_only)
    n = 0
    model_error = 0
    for pred,meas in zip(predictions,dataset.ideal_mean):
      model_error += pow(pred-meas,2)
      n += 1

    return np.sqrt(model_error/n)

  def get_subexpr(self,init_cond=False, \
                  correctable_only=False):
    params = dict(self.params)
    if correctable_only:
      rel = self.spec.get_correctable_model(params)
    else:
      rel = self.spec.get_model(params)


    if self.is_integration_op:
      if init_cond:
        rel = rel.init_cond
      else:
        coeff,all_vars= genoplib.unpack_product(rel.deriv)
        model_vars = list(filter(lambda v: v in self.spec.params, all_vars))
        rel = genoplib.product([genoplib.Const(coeff)] + \
                               list(map(lambda v: genoplib.Var(v), \
                                        model_vars)))


    return rel

  def predict(self,dataset, \
              init_cond=False,
              correctable_only=False):
    inputs = {}
    for k,v in dataset.inputs.items():
      inputs[k] = v
    for k,v in dataset.data.items():
      inputs[k] = v

    params = dict(self.params)

    rel = self.get_subexpr(init_cond=init_cond, \
                           correctable_only=correctable_only)

    n = len(dataset)
    predictions = []
    for idx in range(0,n):
      assigns = dict(map(lambda k : (k,inputs[k][idx]), \
                         inputs.keys()))
      pred = rel.compute(assigns)
      predictions.append(pred)

    return predictions


  @property
  def hidden_cfg(self):
    return runtime_util.get_hidden_cfg(self.block, self.config)


  @property
  def static_cfg(self):
    return runtime_util.get_static_cfg(self.block, self.config)

  # dynamic values (data)
  @property
  def dynamic_cfg(self):
    return runtime_util.get_dynamic_cfg(self.block, self.config)


  

  def get_bounds(self):
    bounds = {}
    for inp in self.block.inputs:
      ival = inp.interval[self.config.mode]
      if ival is None:
        raise Exception("no interval for input %s.<%s> in mode <%s>" \
                        % (self.block.name,inp.name,self.config.mode))
      bounds[inp.name] = [ival.lower,ival.upper]

    for dat in self.block.data:
      ival = dat.interval[self.config.mode]
      if ival is None:
        raise Exception("no interval for datum %s.<%s> in mode <%s>" \
                        % (self.block.name,dat.name,self.config.mode))
      bounds[dat.name] = [ival.lower,ival.upper]

    for out in self.block.outputs:
      ival = out.interval[self.config.mode]
      if ival is None:
        raise Exception("no interval for output %s.<%s> in mode <%s>" \
                        % (self.block.name,out.name,self.config.mode))

      bounds[out.name] = [ival.lower,ival.upper]

    return bounds


  def to_json(self):
    return {
        'block': self.block.name,
        'loc': str(self.loc),
        'output': self.output.name,
        'config': self.config.to_json(),
        'model_error':self._model_error,
        'params': self._params,
        'calib_obj':self.calib_obj.value
    }
  #'phys_model': self.phys_models.to_json(),

  @staticmethod
  def from_json(dev,obj):
    assert(isinstance(dev,devlib.Device))

    blk = dev.get_block(obj['block'])
    loc = devlib.Location.from_string(obj['loc'])
    output = blk.outputs[obj['output']]
    cfg = adplib.BlockConfig.from_json(dev,obj['config'])
    phys = ExpDeltaModel(blk,loc,output,cfg)

    phys._params = obj['params']
    phys._model_error = obj['model_error']
    phys.calib_obj = llenums.CalibrateObjective(obj['calib_obj'])
    return phys



  def __repr__(self):
    return "empirical-delta-model(%s,model_err=%s) :%s" % (self.params, \
                                           self.model_error, \
                                           self.calib_obj.value)


def update(dev,model):
    assert(isinstance(model,ExpDeltaModel))
    #fields['phys_model'] = phys_util.encode_dict(fields['phys_model'])
    where_clause = {
      'block': model.block.name,
      'loc': str(model.loc),
      'output': model.output.name,
      'static_config': model.static_cfg,
      'hidden_config': model.hidden_cfg

    }
    insert_clause = dict(where_clause)
    insert_clause['model'] = runtime_util.encode_dict(model.to_json())
    insert_clause['calib_obj'] = model.calib_obj.value
    insert_clause['model_error'] = model.model_error

    matches = list(dev.physdb \
                   .select(dblib.PhysicalDatabase.DB.DELTA_MODELS,where_clause))
    if len(matches) == 0:
      dev.physdb.insert(dblib.PhysicalDatabase.DB.DELTA_MODELS,insert_clause)
    elif len(matches) == 1:
      dev.physdb.update(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                        where_clause,insert_clause)



def __to_delta_models(dev,matches):
  for match in matches:
    yield ExpDeltaModel.from_json(dev, \
                                  runtime_util.decode_dict(match['model']))


def load(dev,block,loc,output,cfg):
    where_clause = {
      'block': block.name,
      'loc': str(loc),
      'output':output.name,
      'static_config': runtime_util.get_static_cfg(block,cfg),
      'hidden_config': runtime_util.get_hidden_cfg(block,cfg)
    }
    matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS,
                                  where_clause))
    if len(matches) == 1:
      return list(__to_delta_models(dev,matches))[0]
    elif len(matches) == 0:
      pass
    else:
      raise Exception("can only have one match")


def get_models_by_block_config(dev,block,cfg):
  where_clause = {
    'block': block.name,
    'static_config': runtime_util.get_static_cfg(block,cfg)
  }
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                                   where_clause))

  return list(__to_delta_models(dev,matches))
  

def get_calibrated(dev,block,loc,cfg,calib_obj):
  assert(isinstance(calib_obj,llenums.CalibrateObjective))
  where_clause = {
    'block': block.name,
    'loc': str(loc),
    'static_config': runtime_util.get_static_cfg(block,cfg),
    'calib_obj': calib_obj.value
  }
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                                   where_clause))
  return list(__to_delta_models(dev,matches))

def get_all(dev):

  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                                   {}))
  return list(__to_delta_models(dev,matches))

def is_calibrated(dev,block,loc,cfg,calib_obj):
  return not get_calibrated(dev,block,loc,cfg,calib_obj) is None
