import hwlib.physdb as physdb
import hwlib.physdb_util as physutil
import hwlib.adp as adplib
import phys_model.lin_dectree as dectreelib

class ExpPhysModel:
  MODEL_ERROR = "modelError"

  def __init__(self,db,dev,blk,cfg,load_db=True):
    self.dev = dev
    self.block = blk
    self.cfg = cfg
    self.db = db
    self._delta_params = {}
    self._optimize_expr = None
    self.num_samples = 0
    self.label = physutil.PhysModelLabel.NONE
    if load_db:
      self.load()

  @property
  def params(self):
    return dict(self._delta_params)

  def set_param(self,par,delta):
    self._delta_params[par] = delta

  def set_optimize_func(self,func):
    self._optimize_expr = func

  def random_sample(self):
    samples = []
    for par,dectree in self._delta_params.items():
      samples += dectree.random_sample(samples)

    return samples

  @property
  def static_cfg(self):
    return physutil\
      .get_static_cfg(self.block,self.cfg)

  def to_json(self):
    param_dict = {}
    for par,model in self._delta_params.items():
      param_dict[par] = model.to_json()

    return {
      'block': self.block.name,
      'config': self.cfg.to_json(),
      'label': self.label.value,
      'num_samples':self.num_samples,
      'optimize_expr': self._optimize_expr \
      if self._optimize_expr is None else self._optimize_expr.to_json(),
      'params': param_dict,
    }
  #'phys_model': self.phys_models.to_json(),


  def __repr__(self):
    st = "%s\n" % self.cfg
    st += "num-samples: %d\n" % self.num_samples
    st += "opt-expr: %s\n" % self._optimize_expr
    for par,dectree in self._delta_params.items():
      st += "===== %s =====\n" % par
      st += str(dectree.pretty_print())

    return st

  def update(self):
    fields = self.to_json()
    fields['config'] = physutil.encode_dict(fields['config'])
    fields['params'] = physutil.encode_dict(fields['params'])
    fields['static_config'] = self.static_cfg
    #fields['phys_model'] = physutil.encode_dict(fields['phys_model'])
    where_clause = {
      'block': self.block.name,
      'static_config': self.static_cfg
    }

    matches = list(self.db.select(physdb.PhysicalDatabase.DB.PHYS_MODELS,where_clause))
    if len(matches) == 0:
      self.db.insert(physdb.PhysicalDatabase.DB.PHYS_MODELS,fields)
    elif len(matches) == 1:
      self.db.update(physdb.PhysicalDatabase.DB.PHYS_MODELS, where_clause,fields)

  def load(self):
    where_clause = {
      'block': self.block.name,
      'static_config': self.static_cfg
    }
    matches = list(self.db.select(physdb.PhysicalDatabase.DB.PHYS_MODELS,
                                  where_clause))
    if len(matches) == 1:
      row = matches[0]
      mdl = ExpPhysModel.from_json(self.db,self.dev,row)
      self.copy_from(mdl)
    elif len(matches) == 0:
      pass
    else:
      raise Exception("can only have one match")



  def copy_from(self,other):
    assert(self.block.name == other.block.name)
    assert(self.static_cfg == other.static_cfg)
    self.label = other.label
    self.num_samples = other.num_samples
    self._delta_params = dict(other._delta_params)
    self.optimize_expr = other.optimize_expr

  @staticmethod
  def from_json(db,dev,obj):
    blk = dev.get_block(obj['block'])
    cfg_obj = physutil.decode_dict(obj['config'])
    cfg = adplib.BlockConfig.from_json(dev,cfg_obj)

    mdl = ExpPhysModel(db,dev,blk,cfg,load_db=False)
    for par,subobj in physutil.decode_dict(obj['params']).items():
      mdl._delta_params[par] = dectreelib.DecisionNode.from_json(subobj)
    mdl.label = physutil.PhysModelLabel(obj['label'])
    mdl.num_samples = obj['num_samples']
    mdl.optimize_expr = None
    if obj['optimize_expr'] is None:
      mdl.optimize_expr = oplib.Op.from_json(obj['optimize_expr'])
    return mdl

