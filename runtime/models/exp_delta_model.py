import hwlib.hcdc.llenums as llenums

import hwlib.block as blocklib
import hwlib.device as devlib
import hwlib.adp as adplib

import runtime.runtime_util as runtime_util
import runtime.models.database as dblib

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
    self.cfg = cfg
    self._params = {}
    self._model_error = ExpDeltaModel.MAX_MODEL_ERROR
    self.calib_obj = llenums.CalibrateObjective.NONE

  @property
  def delta_spec(self):
    return self.output.deltas[self.cfg.mode]

  @property
  def is_integration_op(self):
    rel = self.spec.get_model(self.params)
    return runtime_lib.is_integration_op(rel)

  @property
  def complete(self):
    for par in self.delta_spec.params:
      if not par in self._params:
        return False
    return True

  def clear(self):
    self.params = {}
    self.model_error = ExpDeltaModel.MAX_MODEL_ERROR

  def bind(self,par,value):
    assert(not par in self.params)
    if not (par in self.spec.params):
      print("WARN: couldn't bind nonexistant parameter <%s> in delta" % par)
      return

    self.params[par] = value

  def error(self,inputs,meas_outputs,init_cond=False):
    pred_outputs = self.predict(inputs, \
                                init_cond=init_cond)
    model_error = 0
    n = 0
    for pred,meas in zip(pred_outputs,meas_outputs):
      model_error += pow(pred-meas,2)
      n += 1

    return np.sqrt(model_error/n)


  def predict(self,inputs, \
              init_cond=False,
              correctable_only=False):
    input_fields = list(inputs.keys())
    input_value_set = list(inputs.values())
    n = len(input_value_set[0])
    outputs = []
    params = dict(self.params)

    if correctable_only:
      rel = self.spec.get_correctable_model(params)
    else:
      rel = self.spec.get_model(params)

    for values in zip(*input_value_set):
      inp_map = dict(list(zip(input_fields,values)) + \
                     list(params.items()))
      if self.integration_op:
        if init_cond:
          output = rel.init_cond.compute(inp_map)
        else:
          output = rel.deriv.compute(inp_map)
      else:
        output = rel.compute(inp_map)
      outputs.append(output)

    return outputs


  @property
  def hidden_cfg(self):
    return runtime_util.get_hidden_cfg(self.block, self.cfg)


  @property
  def static_cfg(self):
    return runtime_util.get_static_cfg(self.block, self.cfg)

  # dynamic values (data)
  @property
  def dynamic_cfg(self):
    return runtime_util.get_dynamic_cfg(self.block, self.cfg)


  

  def get_bounds(self):
    bounds = {}
    for inp in self.block.inputs:
      ival = inp.interval[self.cfg.mode]
      if ival is None:
        raise Exception("no interval for input %s.<%s> in mode <%s>" \
                        % (self.block.name,inp.name,self.cfg.mode))
      bounds[inp.name] = [ival.lower,ival.upper]

    for dat in self.block.data:
      ival = dat.interval[self.cfg.mode]
      if ival is None:
        raise Exception("no interval for datum %s.<%s> in mode <%s>" \
                        % (self.block.name,dat.name,self.cfg.mode))
      bounds[dat.name] = [ival.lower,ival.upper]

    for out in self.block.outputs:
      ival = out.interval[self.cfg.mode]
      if ival is None:
        raise Exception("no interval for output %s.<%s> in mode <%s>" \
                        % (self.block.name,out.name,self.cfg.mode))

      bounds[out.name] = [ival.lower,ival.upper]

    return bounds


  def to_json(self):
    return {
        'block': self.block.name,
        'loc': str(self.loc),
        'output': self.output.name,
        'config': self.cfg.to_json(),
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

    matches = list(dev.physdb \
                   .select(dblib.PhysicalDatabase.DB.DELTA_MODELS,where_clause))
    if len(matches) == 0:
      dev.physdb.insert(dblib.PhysicalDatabase.DB.DELTA_MODELS,insert_clause)
    elif len(matches) == 1:
      dev.physdb.update(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                        where_clause,insert_clause)

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
      return ExpDeltaModel.from_json(dev, \
                                     runtime_util \
                                     .decode_dict(matches[0]['model']))
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
  for match in matches:
    yield ExpDeltaModel.from_json(dev, \
                                  runtime_util \
                                  .decode_dict(match['model']))



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
  if len(matches) == 1:
    yield ExpDeltaModel.from_json(dev, \
                                   runtime_util \
                                   .decode_dict(matches[0]['model']))
  elif len(matches) == 0:
    return None
  else:
    for match in matches:
      ExpDeltaModel.from_json(dev, \
                              runtime_util \
                              .decode_dict(match['model']))

def is_calibrated(dev,block,loc,cfg,calib_obj):
  return not get_calibrated(dev,block,loc,cfg,calib_obj) is None