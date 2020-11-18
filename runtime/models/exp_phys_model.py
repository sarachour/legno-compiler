import hwlib.adp as adplib
import runtime.dectree.dectree as dectreelib
import runtime.runtime_util as runtime_util
import runtime.models.database as dblib

class ExpPhysModel:

  def __init__(self,blk,cfg):
    self.block = blk
    self.cfg = cfg
    self._params = {}
    self._model_error = dectreelib.make_constant(0.0)

  @property
  def model_error(self):
      return self._model_error

  def set_model_error(self,tree):
      assert(isinstance(tree,dectreelib.Node))
      self._model_error = tree

  def set_param(self,par,tree):
      assert(isinstance(tree,dectreelib.Node))
      self._params[par] = tree

  def random_sample(self):
    samples = []
    for par,dectree in self.params.items():
      samples += dectree.random_sample(samples)

    samples += self.model_error.random_sample(samples)

    return samples

  @property
  def static_cfg(self):
    return runtime_util\
      .get_static_cfg(self.block,self.cfg)

  def to_json(self):
    param_dict = {}
    for par,model in self._params.items():
      param_dict[par] = model.to_json()

    return {
      'block': self.block.name,
      'config': self.cfg.to_json(),
      'params': param_dict,
      'model_error':self.model_error.to_json()
    }
  #'phys_model': self.phys_models.to_json(),


  def __repr__(self):
    st = "%s\n" % self.cfg
    for par,dectree in self._params.items():
      st += "===== %s =====\n" % par
      st += str(dectree.pretty_print())

    return st



  def copy_from(self,other):
    assert(self.block.name == other.block.name)
    assert(self.static_cfg == other.static_cfg)
    self.cfg = other.cfg.copy()
    self._params = {}
    for par,tree in other._params.items():
      self._params[par] = tree.copy()
    self.model_error = other.model_error.copy()

  @staticmethod
  def from_json(dev,obj):
    blk = dev.get_block(obj['block'])
    cfg = adplib.BlockConfig.from_json(obj['config'])

    mdl = ExpPhysModel(blk,cfg)
    for par,subobj in obj['params'].items():
      mdl._params[par] = dectreelib.Node.from_json(subobj)

    mdl.model_error = dectreelib.Node.from_json(obj['model_error'])
    return mdl


def __to_phys_models(dev,matches):
  for match in matches:
    yield ExpPhysModel.from_json(dev, \
                                 runtime_util.decode_dict(match['model']))

def load(db,dev,blk,cfg):
    where_clause = {
      'block': self.block.name,
      'static_config': self.static_cfg
    }
    matches = list(self.db.select(dblib \
                                  .PhysicalDatabase \
                                  .DB.PHYS_MODELS,
                                  where_clause))
    if len(matches) == 1:
      return __to_phys_models(dev,matches)[0]

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


