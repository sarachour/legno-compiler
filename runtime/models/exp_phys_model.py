import hwlib.adp as adplib
import runtime.dectree.dectree as dectreelib
import runtime.runtime_util as runtime_util
import runtime.models.database as dblib

class ExpPhysModel:
  MODEL_ERROR = "modelError"

  def __init__(self,blk,cfg):
    self.block = blk
    self.config = cfg
    self._params = {}
    self._model_error = dectreelib.make_constant(0.0)
    self._uncertainties = {}

  @property
  def params(self):
    return dict(self._params.items())

  def variables(self):
    variables = self.params
    variables[ExpPhysModel.MODEL_ERROR] = self._model_error
    return variables

  @property
  def model_error(self):
      return self._model_error

  def uncertainty(self,var):
    if not var in self._uncertainties:
      return 0.0

    return self._uncertainties[var]

  def set_variable(self,name,tree,uncertainty=None):
    if name == ExpPhysModel.MODEL_ERROR:
      self.set_model_error(tree,uncertainty)

    else:
      self.set_param(name,tree)

  def set_uncertainty(self,varname,unc):
    if unc is None:
      return
    assert(isinstance(unc,float))
    self._uncertainties[varname] = unc

  def set_model_error(self,tree,uncertainty=None):
      assert(isinstance(tree,dectreelib.Node))
      self._model_error = tree
      self.set_uncertainty(ExpPhysModel.MODEL_ERROR, uncertainty)

  def set_param(self,par,tree,uncertainty=None):
      assert(isinstance(tree,dectreelib.Node))
      self._params[par] = tree
      self.set_uncertainty(par, uncertainty)

  def random_sample(self):
    samples = []
    for par,dectree in self.params.items():
      samples += dectree.random_sample(samples)

    samples += self.model_error.random_sample(samples)

    return samples

  @property
  def static_cfg(self):
    return runtime_util\
      .get_static_cfg(self.block,self.config)



  def hidden_codes(self):
    for st in filter(lambda st: isinstance(st.impl,blocklib.BCCalibImpl), \
                     self.block.state):
      yield st.name,self.config[st.name].value

  def to_json(self):
    param_dict = {}
    for par,model in self._params.items():
      param_dict[par] = model.to_json()

    return {
      'block': self.block.name,
      'config': self.config.to_json(),
      'params': param_dict,
      'model_error':self._model_error.to_json(),
      'uncertainties':self._uncertainties
    }
  #'phys_model': self.phys_models.to_json(),


  def __repr__(self):
    st = "%s\n" % self.config
    for par,dectree in self._params.items():
      unc = self.uncertainty(par)
      st += "===== %s (unc=%f) =====\n" % (par,unc)
      st += str(dectree.pretty_print())

    return st



  def copy_from(self,other):
    assert(self.block.name == other.block.name)
    assert(self.static_cfg == other.static_cfg)
    self.config = other.cfg.copy()
    self._params = {}
    for par,tree in other._params.items():
      self._params[par] = tree.copy()
    self._model_error = other.model_error.copy()
    self._uncertainties = dict(other._uncertainties)

  @staticmethod
  def from_json(dev,obj):
    blk = dev.get_block(obj['block'])
    cfg = adplib.BlockConfig.from_json(dev,obj['config'])
    assert(not blk is None)
    mdl = ExpPhysModel(blk,cfg)
    for par,subobj in obj['params'].items():
      mdl._params[par] = dectreelib.Node.from_json(subobj)

    mdl._model_error = dectreelib.Node.from_json(obj['model_error'])
    mdl._uncertainties = dict(obj['uncertainties'])
    return mdl


def __to_phys_models(dev,matches):
  for match in matches:
    yield ExpPhysModel.from_json(dev, \
                                 runtime_util.decode_dict(match['model']))

def load(dev,blk,cfg):
    where_clause = {
      'block': blk.name,
      'static_config': runtime_util.get_static_cfg(blk,cfg)
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


