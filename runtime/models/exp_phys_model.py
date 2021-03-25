import hwlib.adp as adplib
import hwlib.block as blocklib

import runtime.runtime_util as runtime_util
import runtime.models.database as dblib

import ops.generic_op as genoplib
import ops.base_op as baseoplib 

import numpy as np
import math
from enum import Enum
import itertools


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
        par = Param(block, \
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


class ErrorParam(Param):

  def __init__(self,block,index,expr,error):
    assert(isinstance(expr,genoplib.Op))
    name = "%s(%s)" % (blocklib.MultiObjective.MODEL_ERROR,index)
    self.index = index
    Param.__init__(self,block,name,expr,error)

class ExpPhysErrorModel:

  def __init__(self,n):
    self._ranges = {}
    self._exprs = {}
    self._errors = {}
    self._n = n
    self._variables = []
    self._values = {}
    self._frozen = False

  @property
  def n(self):
      return self._n

  @property
  def variables(self):
    return list(self._variables)

  def indices(self):
     return list(self._exprs.keys())

  def set_range(self,v,l,u):
    assert(not self._frozen)
    assert(l<u)
    assert(not v in self._variables)
    assert(isinstance(v,str))
    self._ranges[v] = (l,u)
    self._values[v] = list(np.linspace(l,u,self.n))
    self._variables.append(v)


  def has_index(self,idx):
    return idx in self._errors

  def points(self,block):
    for index,expr in self._exprs.items():
        if not expr is None:
            par = ErrorParam(block,index,expr,self._errors[index])
            yield index,par

  def set_expr(self,index,expr,error):
    assert(self._frozen)
    if not (index in self._exprs):
      raise Exception("index <%s> not found in error model" % str(index))

    self._exprs[index] = expr
    self._errors[index] = error

  def clear(self):
    for key in self.errors:
      self._errors[key] = 0.0
      self._exprs[key] = None


  def build(self):
    vals = list(map(lambda v: list(range(self.n)), \
                    self.variables))

    self._frozen = True
    self._errors = {}
    self._exprs= {}
    for idx in itertools.product(*vals):
      self._errors[tuple(idx)] = 0.0
      self._exprs[tuple(idx)] = None


  def exprs_from_json(self,obj):
      errs = dict(map(lambda tup: (tuple(tup[0]),tup[1]), obj['errors']))
      for index,expr_json in obj['exprs']:
          expr = genoplib.Op.from_json(expr_json)
          self.set_expr(tuple(index),expr,errs[tuple(index)])


  @staticmethod
  def from_json(obj):
    mdl = ExpPhysErrorModel(obj['n'])
    mdl._frozen = obj['frozen']
    mdl._ranges = obj['ranges']
    mdl._values = obj['values']
    mdl._errors = dict(map(lambda t: (tuple(t[0]),t[1]), obj['errors']))
    mdl._exprs = dict(map(lambda t: (tuple(t[0]),baseoplib.Op.from_json(t[1])), \
                          obj['exprs']))
    mdl._variables = obj['variables']
    return mdl


  def to_json(self):
    return {
      'frozen': self._frozen,
      'ranges': self._ranges,
      'errors': list(self._errors.items()),
      'exprs': list(map(lambda tup: (tup[0],tup[1].to_json()), \
                        self._exprs.items())),
      'variables':list(self._variables),
      'values':dict(self._values),
      'n':self.n
    }



class ExpPhysModel:
  #MODEL_ERROR = "modelError"
  NOISE= "noise"

  def __init__(self,blk,cfg,output,n=10):
    self.block = blk
    self.config = cfg
    self.output = output
    self._params= {}
    self._model_error = ExpPhysErrorModel(n)
    self._noise = None

    if self.spec.is_integration_op:
        rel,_,_ = self.spec.get_integration_exprs()
    else:
        rel = self.spec.relation

    for name in filter(lambda v: self.block.inputs.has(v) , rel.vars()):
        ival = self.block.inputs[name].interval[self.config.mode]
        self._model_error.set_range(name, ival.lower,ival.upper)

    for name in filter(lambda v: self.block.data.has(v), rel.vars()):
        ival = self.block.data[name].interval[self.config.mode]
        self._model_error.set_range(name, ival.lower,ival.upper)

    self._model_error.build()

  @property
  def spec(self):
    return self.output.deltas[self.config.mode]

  @property
  def params(self):
    return dict(self._params.items())

  def variables(self):
    variables = dict(list(self.params.items())) 

    if not self.noise is None:
        variables[ExpPhysModel.NOISE] = self._noise

    return variables

  @property
  def noise(self):
      return self._noise


  @property
  def model_error(self):
      return self._model_error

  def set_variable(self,name,expr,error):
    if name == ExpPhysModel.NOISE:
      self.set_noise(expr,error)
    else:
      self.set_param(name,expr,error)

  def set_noise(self,expr,error):
      assert(isinstance(expr,baseoplib.Op))
      assert(isinstance(error,float))
      self._noise = Param(self.block,ExpPhysModel.NOISE, expr,error)


  def set_param(self,par,expr,error):
      assert(isinstance(expr,baseoplib.Op))
      assert(isinstance(error,float))
      self._params[par] = Param(self.block, par, expr, error)

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
      'model_error': self._model_error.to_json(),
      'noise':None if self._noise is None else self._noise.to_json()
    }
  #'phys_model': self.phys_models.to_json(),


  @staticmethod
  def from_json(dev,obj):
    blk = dev.get_block(obj['block'])
    cfg = adplib.BlockConfig.from_json(dev,obj['config'])
    out = blk.outputs[obj['output']]
    assert(not blk is None)
    try:
        mdl = ExpPhysModel(blk,cfg,out,obj['model_error']['n'])
    except Exception as e:
        mdl = ExpPhysModel(blk,cfg,out,0)

    mdl._model_error.build()
    mdl._model_error.exprs_from_json(obj['model_error'])
    try:
        mdl._model_error.exprs_from_json(obj['model_error'])
    except Exception as e:
        print("[warn] phys.from_json: can't load model error expressions from json <%s>" % e)

    for par,subobj in obj['params'].items():
      mdl._params[par] = Param.from_json(blk,subobj)

    if "noise" in obj and not obj['noise'] is None:
        mdl._noise = Param.from_json(blk,obj['noise'])

    return mdl


class ExpPhysModelClause(Enum):
  BLOCK = "block"
  OUTPUT = "output"
  STATIC_CONFIG = "static_config"


def __to_phys_models(dev,matches):
  for match in matches:
    yield ExpPhysModel.from_json(dev, \
                                 runtime_util.decode_dict(match['model']))

def get_models(dev,fields,block=None,config=None,output=None):
    where_clause = {}
    for field_name in fields:
       field = ExpPhysModelClause(field_name)
       if field == ExpPhysModelClause.BLOCK:
          assert(isinstance(block,blocklib.Block))
          where_clause['block'] = block.name
       elif field == ExpPhysModelClause.STATIC_CONFIG:
          assert(isinstance(block,blocklib.Block))
          assert(isinstance(config,adplib.BlockConfig))
          where_clause['static_config'] = runtime_util.get_static_cfg(block,config)
       elif field == ExpPhysModelClause.OUTPUT:
          where_clause['output'] = output.name

    matches = list(dev.physdb.select(dblib \
                                  .PhysicalDatabase \
                                  .DB.PHYS_MODELS,
                                  where_clause))

    return list(__to_phys_models(dev,matches))

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


