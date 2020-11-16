import hwlib.physdb as physdb
import hwlib.physdb_util as physutil
import hwlib.adp as adplib
import phys_model.lin_dectree as dectreelib

class ExpPhysModel:

  def __init__(self,db,dev,blk,cfg,load_db=True):
    self.block = blk
    self.cfg = cfg
    self._params = {}
    self._model_error = dectreelib.make_constant(0.0)

  @property
  def model_error(self):
      return self._model_error

  def set_model_error(self,tree):
      assert(isinstance(tree,dectree.Node))
      self._model_error = tree

  def set_param(self,par,tree):
      assert(isinstance(delta,dectree.Node))
      self.params[par] = tree

  def random_sample(self):
    samples = []
    for par,dectree in self.params.items():
      samples += dectree.random_sample(samples)

    samples += self.model_error.random_sample(samples)

    return samples

  @property
  def static_cfg(self):
    return physutil \
      .get_static_cfg(self.block,self.cfg)

  def to_json(self):
    param_dict = {}
    for par,model in self.params.items():
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
    self.label = other.label
    self.num_samples = other.num_samples
    self._delta_params = dict(other._delta_params)
    self.optimize_expr = other.optimize_expr

  @staticmethod
  def from_json(obj):
    blk = dev.get_block(obj['block'])
    cfg_obj = physutil.decode_dict(obj['config'])
    cfg = adplib.BlockConfig.from_json(cfg_obj)

    mdl = ExpPhysModel(db,dev,blk,cfg,load_db=False)
    for par,subobj in physutil.decode_dict(obj['params']).items():
      mdl._delta_params[par] = dectreelib.DecisionNode.from_json(subobj)
    mdl.label = physutil.PhysModelLabel(obj['label'])
    mdl.num_samples = obj['num_samples']
    mdl.optimize_expr = None
    if obj['optimize_expr'] is None:
      mdl.optimize_expr = oplib.Op.from_json(obj['optimize_expr'])
    return mdl


# get data for physical model
def get_dataset(db,model):
    raise NotImplementedError

def load(db,dev,blk,cfg):
    where_clause = {
      'block': self.block.name,
      'static_config': self.static_cfg
    }
    matches = list(self.db.select(physdb.PhysicalDatabase.DB.PHYS_MODELS,
                                  where_clause))
    if len(matches) == 1:
      row = matches[0]
      mdl = ExpPhysModel.from_json(self.db,dev,row)
      return mdl

    elif len(matches) == 0:
      pass
    else:
      raise Exception("can only have one match")

def update(db,model):
    assert(isinstance(model,ExpPhysModel))
    fields = physutil.encode_dicts(model.to_json())

    where_clause = {
      'block': self.block.name,
      'static_config': self.static_cfg
    }

    matches = list(self.db.select(physdb.PhysicalDatabase.DB.PHYS_MODELS,where_clause))
    if len(matches) == 0:
      self.db.insert(physdb.PhysicalDatabase.DB.PHYS_MODELS,fields)
    elif len(matches) == 1:
      self.db.update(physdb.PhysicalDatabase.DB.PHYS_MODELS, where_clause,fields)


