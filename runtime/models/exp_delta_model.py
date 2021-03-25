import ops.generic_op as genoplib

import hwlib.hcdc.llenums as llenums

import hwlib.block as blocklib
import hwlib.device as devlib
import hwlib.adp as adplib

import runtime.runtime_util as runtime_util
import runtime.models.database as dblib

import numpy as np
from enum import Enum
import itertools
import math

class  ExpDeltaErrorModel:

  def __init__(self,n):
    self._ranges = {}
    self._errors = {}
    self._n = n
    self._variables = []
    self._values = {}
    self._frozen = False
    self._expo = 4

  def set_range(self,v,l,u):
    assert(not self._frozen)
    assert(l<u)
    assert(not v in self._variables)
    assert(isinstance(v,str))
    self._ranges[v] = (l,u)
    self._values[v] = list(np.linspace(l,u,self.n))
    self._variables.append(v)
    self._errors = {}

  def indices(self):
    return list(self._errors.keys())

  def set_error(self,index,error):
    assert(self._frozen)
    if not index in self._errors:
      raise Exception("index not in error map <%s>" % str(index))

    if not all(map(lambda i: i < self.n and i >= 0, index)):
      raise Exception("index isn't consistent with size index=%s n=%s" \
                      % (index,self.n))

    self._errors[index] = error

  def errors(self):
    assert(self._frozen)
    return dict(self._errors)

  @property
  def n(self):
    return self._n

  @n.setter
  def n(self,val):
    if val == self.n:
      return

    self._n = val
    for v,(l,u) in self._ranges.items():
      self._values[v] = list(np.linspace(l,u,self.n))

    self._errors = {}
    self._frozen = False
    self.build()

  @property
  def avg_error(self):
    return np.mean(list(self._errors.values()))

  @property
  def min_error(self):
    return min(self._errors.values()) if len(self._errors.values()) > 0 else \
      0.0

  @property
  def max_error(self):
    return max(self._errors.values()) if len(self._errors.values()) > 0 else \
      0.0

  @property
  def variables(self):
    return list(self._variables)

  def get_distance(self,index,inputs):
    vardict = self.get_point(index)
    for var,i in zip(self.variables,index):
        vardict[var] = self._values[var][i]

    dist = 0.0
    for inp,value in filter(lambda tup: tup[0] in inputs, vardict.items()):
      dist += (value-inputs[inp])**2

    dist = math.sqrt(dist)**self._expo
    return dist

  def get_weight(self,index,inputs):
    dist = self.get_distance(index,inputs)
    return math.exp(-dist)/math.exp(0)

  def get_error(self,inputs):
    numer,denom = 0.0,0.0
    for indices,point_inputs in self.points():
      error = self._errors[indices]
      dist = 0.0
      for inp,value in filter(lambda tup: tup[0] in inputs, point_inputs.items()):
        dist += (value-inputs[inp])**2

        dist = math.sqrt(dist)**self._expo
        if dist == 0:
          return error

        numer += error*dist
        denom += dist

    return numer/denom

  def get_point(self,idx):
    if not idx in self._errors:
      raise Exception("unknown index <%s> in error model" % (str(index)))

    vardict = {}
    for var,i in zip(self.variables,idx):
      vardict[var] = self._values[var][i]
    return vardict

  def points(self):
    assert(self._frozen)
    for idx in self._errors.keys():
      vardict = self.get_point(idx)
      yield idx,vardict


  def clear(self):
    for key in self._errors:
      self._errors[key] = 0.0

  def build(self):
    vals = list(map(lambda v: list(range(self.n)), \
                    self.variables))

    self._frozen = True
    self._errors = {}
    for idx in itertools.product(*vals):
      self._errors[tuple(idx)] = 0.0

  def data_from_json(self,obj):
    for idx,err in obj['errors']:
      self.set_error(tuple(idx),err)


  @staticmethod
  def from_json(obj):
    mdl = ExpDeltaErrorModel(obj['n'])
    mdl._frozen = obj['frozen']
    mdl._ranges = obj['ranges']
    mdl._values = obj['values']
    mdl._variables = obj['variables']
    mdl.build()

    for idx,err in obj['errors']:
      mdl.set_error(tuple(idx),err)

    return mdl

  def to_json(self):
    return {
      'frozen': self._frozen,
      'ranges': self._ranges,
      'errors': list(self._errors.items()),
      'variables':list(self._variables),
      'values':dict(self._values),
      'n':self.n
    }


  def __len__(self):
    return self.n**len(self.variables)


  def __repr__(self):
    return "err-mdl(rng=[%f,%f],mean=%f,n=%d)" \
      % (self.min_error,self.max_error,self.avg_error,self.n)


class ExpDeltaModel:
  #MODEL_ERROR = "modelError"
  NOISE = "noise"

  def __init__(self,blk,loc,output,cfg,calib_obj,n):
    assert(isinstance(blk,blocklib.Block))
    assert(isinstance(loc,devlib.Location))
    assert(isinstance(output,blocklib.BlockOutput))
    assert(isinstance(cfg,adplib.BlockConfig))
    assert(isinstance(calib_obj,llenums.CalibrateObjective))
    self.block = blk
    self.loc = loc
    self.output = output
    self.config = cfg
    self._params = {}

    self._noise = 0.0
    self.calib_obj = calib_obj

    if self.spec.is_integration_op:
      rel,_,_ = self.spec.get_integration_exprs()
    else:
      rel = self.spec.relation.copy()

    self._model_error = ExpDeltaErrorModel(n)
    for name in filter(lambda v: self.block.inputs.has(v) , rel.vars()):
        ival = self.block.inputs[name].interval[self.config.mode]
        self._model_error.set_range(name, ival.lower,ival.upper)

    for name in filter(lambda v: self.block.data.has(v), rel.vars()):
        ival = self.block.data[name].interval[self.config.mode]
        self._model_error.set_range(name, ival.lower,ival.upper)

    self._model_error.build()


  @property
  def params(self):
    return dict(self._params)

  def variables(self):
    variables = self.params
    #variables[ExpDeltaModel.MODEL_ERROR] = self.model_error
    variables[ExpDeltaModel.NOISE] = self.noise
    return variables

  def has_value(self,varname):
    return varname in self._params or \
      varname == ExpDeltaModel.NOISE

  def get_value(self,varname):
    if varname in self._params:
      return self._params[varname]

    if varname == ExpDeltaModel.NOISE:
      return self._noise

    raise Exception("unknown variable <%s> (pars:%s)" \
                    % (varname,self._params.keys()))

  @property
  def spec(self):
    return self.output.deltas[self.config.mode]

  @property
  def noise(self):
    return self._noise


  @property
  def model_error(self):
    return self._model_error

  @property
  def relation(self):
    return self.spec.relation

  @property
  def is_integration_op(self):
    return self.spec.is_integration_op
    rel = self.spec.get_model(self.params)
    return runtime_util.is_integration_op(rel)

  def is_concrete(self,variables):
    for var in variables:
      if var in self.spec.params and \
         not var in self._params:
        return False

    return True

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
    self._params = {}
    self._model_error.clear()
    self._noise = 0.0

  def bind(self,par,value):
    if not (par in self.spec.params):
      print("WARN: couldn't bind nonexistant parameter <%s> in delta" % par)
      return

    self._params[par] = value

  def set_noise(self,noise):
    self._noise = noise

  def errors(self,dataset,init_cond=False,correctable_only=False):
    predictions = self.predict(dataset, \
                               init_cond=init_cond, \
                               correctable_only=correctable_only)
    n = 0
    errors = []
    for pred,meas in zip(predictions,dataset.meas_mean):
      errors.append(meas-pred)

    return errors


  def error(self,dataset,init_cond=False,correctable_only=False):
    predictions = self.predict(dataset, \
                               init_cond=init_cond, \
                               correctable_only=correctable_only)
    errors = self.errors(dataset,init_cond,\
                         correctable_only)
    model_error = sum(map(lambda err: pow(err,2), errors))
    return np.sqrt(model_error/len(errors))

  def get_subexpr(self,init_cond=False, \
                  correctable_only=False, \
                  concrete=True):
    def conc(rel,pars):
      return rel.substitute(dict(map(lambda tup: (tup[0],genoplib.Const(tup[1])), \
                                     pars.items())))

    params = dict(self.params)
    if not concrete:
       params = {}

    if correctable_only:
      params = self.spec.get_correctable_params(params)

    if self.spec.is_integration_op:
      ic,deriv_gain,deriv_offset = self.spec.get_integration_exprs()
      if init_cond:
        return conc(ic,params)
      else:
        return conc(deriv_gain,params),conc(deriv_offset,params)

    else:
      return conc(self.spec.relation,params)


  def predict(self,dataset, \
              init_cond=False,
              correctable_only=False):
    inputs = dataset.get_inputs()
    params = dict(self.params)

    if not init_cond and self.spec.is_integration_op:
      # return gain
      rel, _ = self.get_subexpr(init_cond=init_cond, \
                                correctable_only=correctable_only)
    else:
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


  def hidden_codes(self):
    for st in filter(lambda st: isinstance(st.impl,blocklib.BCCalibImpl), \
                     self.block.state):
      yield st.name,self.config[st.name].value

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
        'model_error':self._model_error.to_json(),
        'noise':self._noise,
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
    calib_obj = llenums.CalibrateObjective(obj['calib_obj'])

    try:
      phys = ExpDeltaModel(blk,loc,output,cfg,calib_obj,obj['model_error']['n'])
    except:
      phys = ExpDeltaModel(blk,loc,output,cfg,calib_obj,0)

    phys._params = obj['params']
    try:
      phys._noise= obj['noise']
    except:
      print("[warn] can't parse noise")
      pass

    phys._model_error.build()
    try:
      phys._model_error.data_from_json(obj['model_error'])
    except Exception as e:
      print("[warn] can't load model errors <%s>" % e)
      pass

    return phys



  def __repr__(self):
    return "empirical-delta-model(%s,model_err=%s,noise=%s) :%s" % (self.params, \
                                           self.model_error, \
                                           self.noise, \
                                           self.calib_obj.value)


def __to_delta_models(dev,matches):
  for match in matches:
    ExpDeltaModel.from_json(dev, \
                                    runtime_util.decode_dict(match['model']))

    try:
      yield ExpDeltaModel.from_json(dev, \
                                    runtime_util.decode_dict(match['model']))
    except Exception as e:
      print("[warn] threw error when unpacking delta model: %s" % e)
      continue

def update(dev,model):
    assert(isinstance(model,ExpDeltaModel))
    #fields['phys_model'] = phys_util.encode_dict(fields['phys_model'])
    where_clause = {
      'block': model.block.name,
      'loc': str(model.loc),
      'output': model.output.name,
      'static_config': model.static_cfg,
      'hidden_config': model.hidden_cfg,
      'calib_obj': model.calib_obj.value

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
    else:
      raise Exception("cannot haave more than one match")



def load(dev,block,loc,output,cfg,calib_obj):

    if calib_obj is None:
      raise Exception("no calibration objective specified")

    where_clause = {
      'block': block.name,
      'loc': str(loc),
      'output':output.name,
      'static_config': runtime_util.get_static_cfg(block,cfg),
      'hidden_config': runtime_util.get_hidden_cfg(block,cfg),
      'calib_obj': calib_obj.value
    }

    matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS,
                                  where_clause))
    if len(matches) == 1:
      return list(__to_delta_models(dev,matches))[0]
    elif len(matches) == 0:
      pass
    else:
      raise Exception("can only have one match")


class ExpDeltaModelClause(Enum):
  BLOCK = "block"
  LOC = "loc"
  OUTPUT = "output"
  STATIC_CONFIG = "static_config"
  CALIB_OBJ = "calib_obj"
  HIDDEN_CONFIG = "hidden_config"

def _derive_where_clause(clauses,block,loc,output,cfg,calib_obj):
  def test_if_null(qty,msg):
    if qty is None:
      raise Exception(msg)

  where_clause = {}
  for clause in clauses:
    cls = ExpDeltaModelClause(clause)
    if cls == ExpDeltaModelClause.BLOCK:
      test_if_null(block, "get_models: expected block.")
      where_clause['block'] = block.name

    elif cls == ExpDeltaModelClause.LOC:
      test_if_null(loc, "get_models: expected loc.")
      where_clause['loc'] = str(loc)

    elif cls == ExpDeltaModelClause.OUTPUT:
      test_if_null(loc,"get_models: expected output")
      where_clause['output'] =output.name

    elif cls == ExpDeltaModelClause.STATIC_CONFIG:
      test_if_null(cfg,"get_models: expected config")
      where_clause['static_config'] =runtime_util.get_static_cfg(block,cfg)

    elif cls == ExpDeltaModelClause.HIDDEN_CONFIG:
      test_if_null(cfg,"get_models: expected config")
      where_clause['hidden_config'] =runtime_util.get_hidden_cfg(block,cfg)

    elif cls == ExpDeltaModelClause.CALIB_OBJ:
      test_if_null(calib_obj,"get_models: expected calibration objective")
      assert(isinstance(calib_obj,llenums.CalibrateObjective))
      where_clause['calib_obj'] =calib_obj.value
    else:
      raise Exception("unknown??")

  return where_clause

def get_models(dev,clauses,block=None,loc=None,output=None,config=None,calib_obj=None):
  where_clause = _derive_where_clause(clauses,block,loc,output,config,calib_obj)
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, where_clause))
  models = list(__to_delta_models(dev,matches))
  return models


def remove_models(dev,clauses,block=None,loc=None,output=None,config=None,calib_obj=None):
  where_clause = _derive_where_clause(clauses,block,loc,output,config,calib_obj)
  dev.physdb.delete(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                    where_clause)

def get_all(dev):
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, {}))
  return list(__to_delta_models(dev,matches))


'''
def get_calibrated_output(dev,block,loc,output,cfg,calib_obj):
  if calib_obj is None:
    raise Exception("no calibration objective specified")

  assert(isinstance(calib_obj,llenums.CalibrateObjective))
  where_clause = {
    'block': block.name,
    'loc': str(loc),
    'output': output.name,
    'static_config': runtime_util.get_static_cfg(block,cfg),
    'calib_obj': calib_obj.value
  }
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                                   where_clause))
  models = list(__to_delta_models(dev,matches))
  if len(models) == 1:
    return models[0]
  elif len(models) == 0:
    return None
  elif len(models) > 1 and calib_obj != llenums.CalibrateObjective.NONE:
    raise Exception("cannot have more than one delta model per calibration objective")
  else:
    return models


def get_calibrated(dev,block,loc,cfg,calib_obj):
  if calib_obj is None:
    raise Exception("no calibration objective specified")

  assert(isinstance(calib_obj,llenums.CalibrateObjective))
  where_clause = {
    'block': block.name,
    'loc': str(loc),
    'static_config': runtime_util.get_static_cfg(block,cfg),
    'calib_obj': calib_obj.value
  }
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                                   where_clause))
  models = list(__to_delta_models(dev,matches))
  return models

def remove_by_calibration_objective(dev,calib_obj):
  if calib_obj is None:
    raise Exception("no calibration objective specified")

  assert(isinstance(calib_obj,llenums.CalibrateObjective))
  where_clause = {
    'calib_obj': calib_obj.value
  }
  dev.physdb.delete(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                    where_clause)

def get_models_by_calibration_objective(dev,calib_obj):
  where_clause = {
    'calib_obj': calib_obj.value
  }
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, where_clause))
  return list(__to_delta_models(dev,matches))


def get_all(dev):
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, {}))
  return list(__to_delta_models(dev,matches))

def is_calibrated(dev,block,loc,cfg,calib_obj):
  return len(get_calibrated(dev, block, \
                            loc, \
                            cfg, \
                            calib_obj)) > 0

def get_models_by_block_instance(dev,block,loc,cfg):
  where_clause = {
    'block': block.name,
    'loc': str(loc),
    'static_config': runtime_util.get_static_cfg(block,cfg)
  }
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                                   where_clause))
  return list(__to_delta_models(dev,matches))


def get_models_by_block_config(dev,block,cfg):
  where_clause = {
    'block': block.name,
    'static_config': runtime_util.get_static_cfg(block,cfg)
  }
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                                   where_clause))

  return list(__to_delta_models(dev,matches))




def get_models_by_fully_configured_block_instance(dev,block,loc,cfg):
  where_clause = {
    'block': block.name,
    'loc': str(loc),
    'static_config': runtime_util.get_static_cfg(block,cfg),
    'hidden_config': runtime_util.get_hidden_cfg(block,cfg)
  }
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                                   where_clause))
  models = list(__to_delta_models(dev,matches))
  return models



def get_fully_configured_outputs(dev,block,loc,output,cfg):
  where_clause = {
    'block': block.name,
    'loc': str(loc),
    'output': output.name,
    'static_config': runtime_util.get_static_cfg(block,cfg),
    'hidden_config': runtime_util.get_hidden_cfg(block,cfg)
  }
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.DELTA_MODELS, \
                                   where_clause))
  models = list(__to_delta_models(dev,matches))
  return models

'''
