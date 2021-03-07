import hwlib.adp as adplib
import hwlib.block as blocklib

import runtime.dectree.dectree as dectreelib
import runtime.runtime_util as runtime_util
import runtime.models.database as dblib

import ops.generic_op as genoplib
import ops.base_op as baseoplib 

import numpy as np
import math



class ExpPhysModel:
  MODEL_ERROR = "modelError"
  NOISE= "noise"

  class Param:

      def __init__(self,block,var_name,expr,error):
          self._variable = var_name
          self._hidden_codes = list(map(lambda st: st.name, \
                                        runtime_util.get_hidden_codes(block)))
          self._expr = expr
          self._params = list(filter(lambda v: not v in self._hidden_codes, \
                                     self._expr.vars()))
          self._error = error

      @property
      def params(self):
          return self._params

      @property
      def error(self):
         return self._error

      @property
      def expr(self):
          return self._expr

      @staticmethod
      def from_json(block,obj):
          expr = baseoplib.Op.from_json(obj['expr'])
          par = ExpPhysModel.Param(block, \
                                   obj['variable'],  \
                                   expr=expr, \
                                   error=obj['error'])
          return par

      def to_json(self):
         return {
             'variable': self._variable, \
             'expr': self.expr.to_json(), \
             'error': self.error
         }

      def __repr__(self):
         return "var %s %s pars=%s score=%f" % (self._variable, \
                                                self.expr,self._params,self.error)


  def __init__(self,blk,cfg,output):
    self.block = blk
    self.config = cfg
    self.output = output
    self._params= {}
    self._model_error = None
    self._noise = None


  @property
  def params(self):
    return dict(self._params.items())

  def variables(self):
    variables = dict(list(self.params.items())) 
    if not self.model_error is None:
        variables[ExpPhysModel.MODEL_ERROR] = self._model_error

    if not self.model_error is None:
        variables[ExpPhysModel.NOISE] = self._noise


    return variables

  @property
  def noise(self):
      return self._noise


  @property
  def model_error(self):
      return self._model_error

  def set_variable(self,name,expr,error):
    if name == ExpPhysModel.MODEL_ERROR:
      self.set_model_error(expr,error)
    elif name == ExpPhysModel.NOISE:
      self.set_noise(expr,error)
    else:
      self.set_param(name,expr,error)

  def set_noise(self,expr,error):
      assert(isinstance(expr,baseoplib.Op))
      assert(isinstance(error,float))
      self._noise = ExpPhysModel.Param(self.block, \
                                              ExpPhysModel.NOISE, expr,error)


  def set_model_error(self,expr,error):
      assert(isinstance(expr,baseoplib.Op))
      assert(isinstance(error,float))
      self._model_error  = ExpPhysModel.Param(self.block, \
                                              ExpPhysModel.MODEL_ERROR, expr,error)

  def set_param(self,par,expr,error):
      assert(isinstance(expr,baseoplib.Op))
      assert(isinstance(error,float))
      self._params[par] = ExpPhysModel.Param(self.block, \
                                             par, expr, error)

  def min_samples(self):
      nsamps = []
      for mdl in self.variables().values():
          nsamps.append(len(mdl.params)+1)

      return max(nsamps)

  @property
  def static_cfg(self):
    return runtime_util\
      .get_static_cfg(self.block,self.config)

  def __repr__(self):
    st = "%s\n" % self.config
    for par,param in self._params.items():
        st += "%s\n" % (param)
    st += "== model error ==\n"
    st += "%s\n" % self._model_error
    st += "== noise ==\n"
    st += "%s\n" % self._noise
    return st


  def to_json(self):
    param_dict = {}
    for par,model in self._params.items():
      param_dict[par] = model.to_json()

    assert(not self._noise is None)
    return {
      'block': self.block.name,
      'output': self.output.name,
      'config': self.config.to_json(),
      'params': param_dict,
      'model_error':None if self._model_error is None else self._model_error.to_json(),
      'noise':None if self._noise is None else self._noise.to_json()
    }
  #'phys_model': self.phys_models.to_json(),


  @staticmethod
  def from_json(dev,obj):
    blk = dev.get_block(obj['block'])
    cfg = adplib.BlockConfig.from_json(dev,obj['config'])
    out = blk.outputs[obj['output']]
    assert(not blk is None)
    mdl = ExpPhysModel(blk,cfg,out)
    for par,subobj in obj['params'].items():
      mdl._params[par] = ExpPhysModel.Param.from_json(blk,subobj)

    if "model_error" in obj and not obj['model_error'] is None:
        mdl._model_error = ExpPhysModel.Param.from_json(blk,obj['model_error'])
 
    if "noise" in obj and not obj['noise'] is None:
        mdl._noise = ExpPhysModel.Param.from_json(blk,obj['noise'])

    return mdl


def __to_phys_models(dev,matches):
  for match in matches:
    yield ExpPhysModel.from_json(dev, \
                                 runtime_util.decode_dict(match['model']))

def load(dev,blk,cfg,output):
    where_clause = {
        'block': blk.name,
        'static_config': runtime_util.get_static_cfg(blk,cfg), \
        'output': output.name
    }
    matches = list(dev.physdb.select(dblib \
                                  .PhysicalDatabase \
                                  .DB.PHYS_MODELS,
                                  where_clause))
    if len(matches) == 1:
      return list(__to_phys_models(dev,matches))[0]

    elif len(matches) == 0:
      pass
    else:
      raise Exception("can only have one match")

def update(dev,model):
    assert(isinstance(model,ExpPhysModel))
    where_clause = {
        'block': model.block.name,
        'output': model.output.name,
        'static_config': model.static_cfg
    }
    insert_clause = dict(where_clause)
    insert_clause['model'] = runtime_util \
                             .encode_dict(model.to_json())

    matches = list(dev.physdb.select(dblib\
                                     .PhysicalDatabase \
                                     .DB.PHYS_MODELS,where_clause))
    if len(matches) == 0:
      dev.physdb.insert(dblib \
                        .PhysicalDatabase \
                        .DB.PHYS_MODELS,insert_clause)
    elif len(matches) == 1:
      dev.physdb.update(dblib \
                        .PhysicalDatabase \
                        .DB.PHYS_MODELS, \
                        where_clause, insert_clause)


