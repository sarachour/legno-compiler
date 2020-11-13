from hwlib.delta_model import ExpCfgBlock
import hwlib.physdb_util as physutil
import hwlib.physdb as physdb

class NotCalibratedException(Exception):

  def __init__(self):
    Exception.__init__(self)

def get_configured_physical_block(db,dev,blk,inst,cfg):
  static_cfg = physutil.get_static_cfg(blk,cfg)
  where_clause = {'block':blk.name, \
                  'loc':str(inst), \
                  'static_config':static_cfg}

  # compute costs
  for row in db.select(physdb.PhysicalDatabase.DB.DELTA_MODELS, \
                       where_clause):
    phys = ExpCfgBlock.from_json(db,dev,row)
    yield phys



def get_calibrated_configured_physical_block(db,dev,blk,inst,cfg,label):
  assert(isinstance(label,physutil.DeltaModelLabel))
  static_cfg = physutil.get_static_cfg(blk,cfg)
  where_clause = {'block':blk.name, \
                  'loc':str(inst), \
                  'static_config':static_cfg, \
                  'label':label.value}

  # compute costs
  for row in db.select(physdb.PhysicalDatabase.DB.DELTA_MODELS, \
                       where_clause):
    phys = ExpCfgBlock.from_json(db,dev,row)
    yield phys

def get_by_block_configuration(db,dev,blk,cfg,hidden=False):
  where_clause = {'block':blk.name, \
  }

  if not cfg is None:
    static_cfg = physutil.get_static_cfg(blk,cfg)
    where_clause['static_config'] = static_cfg
    if hidden:
      hidden_cfg = physutil.get_hidden_cfg(blk,cfg)
      where_clause['hidden_config'] = hidden_cfg


  for row in db.select(physdb.PhysicalDatabase.DB.DELTA_MODELS, where_clause):
    yield ExpCfgBlock.from_json(db,dev,row)


def get_by_block_instance(db,dev,blk,inst,cfg=None,hidden=False):
  where_clause = {'block':blk.name, \
                  'loc':str(inst) \
  }

  if not cfg is None:
    static_cfg = physutil.get_static_cfg(blk,cfg)
    where_clause['static_config'] = static_cfg
    if hidden:
      hidden_cfg = physutil.get_hidden_cfg(blk,cfg)
      where_clause['hidden_config'] = hidden_cfg


  for row in db.select(physdb.PhysicalDatabase.DB.DELTA_MODELS, where_clause):
    yield ExpCfgBlock.from_json(db,dev,row)


def get_all(db,dev):
  for row in db.select({}):
    yield ExpCfgBlock.from_json(db,dev,row)

# get concretization of physical model
def get_physical_models(db,dev,blk,inst,cfg=None):
  where_clause = {'block':blk.name, \
                  'loc':str(inst) \
  }

  if not cfg is None:
    static_cfg = ExpCfgBlock.get_static_cfg(blk,cfg)
    where_clause['static_config'] = static_cfg

  for row in db.select(physdb.PhysicalDatabase.DB.DELTA_MODELS, where_clause):
    return ExpCfgBlock.from_json(db,dev,row).phys_models

