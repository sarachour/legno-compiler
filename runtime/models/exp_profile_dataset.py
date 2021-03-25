import hwlib.hcdc.llenums as llenums

import hwlib.block as blocklib
import hwlib.device as devlib
import hwlib.adp as adplib

import runtime.runtime_util as runtime_util
import runtime.models.database as dblib
import ops.generic_op as genoplib
import ops.op as oplib
from enum import Enum

import util.util as util

class ExpProfileDataset:

  def __init__(self,block,loc,output,cfg,method):
    self.block = block
    self.loc = loc
    self.config = cfg
    self.output = output
    self.method = method

    # inputs
    self.data = {}
    self.inputs = {}
    self.ideal_mean = []
    self.meas_mean = []
    self.meas_stdev = []



    variables = self.relation().vars()
    for input_port in self.block.inputs:
      if input_port.name in variables:
        self.inputs[input_port.name] = []

    for stmt in self.config.stmts:
      if stmt.type == adplib.ConfigStmtType.CONSTANT:
        self.data[stmt.name] = []

    assigned = list(self.inputs.keys()) + list(self.data.keys())
    for v in variables:
      if not v in assigned:
        raise Exception("unknown variable: %s" % v)

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


  def get_input(self,idx):
    inputs = {}
    for k,v in self.inputs.items():
      inputs[k] = v[idx]

    for k,v in self.data.items():
      assert(not k in inputs)
      quant,ival = self.block.data[k].quantize[self.config.mode], \
        self.block.data[k].interval[self.config.mode]
      inputs[k] = quant.round_value(ival,v[idx])

    return inputs


  def get_inputs(self):
    inputs = {}
    for k,v in self.inputs.items():
      inputs[k] = v
 
    for k,v in self.data.items():
      assert(not k in inputs)
      quant,ival = self.block.data[k].quantize[self.config.mode], \
        self.block.data[k].interval[self.config.mode]
      roundit = lambda v: quant.round_value(ival,v)
      inputs[k] = list(map(lambda vi: roundit(vi), v))

    return inputs


  def relation(self):
      rel = self.output.relation[self.config.mode]
      if genoplib.is_integration_op(rel):
          if self.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
              integ_expr = genoplib.unpack_integ(rel)
              return integ_expr.init_cond
          elif self.method == llenums.ProfileOpType.INTEG_DERIVATIVE_GAIN:
              return genoplib.Const(1.0)
          else:
              return genoplib.Const(0.0)
      else:
          return rel




  def add(self,config,inputs,mean,std):
    assigns = {}
    for input_name in self.inputs.keys():
      self.inputs[input_name].append(inputs[input_name])
      assigns[input_name] = self.inputs[input_name][-1]

    for data_name in self.data.keys():
      value = config[data_name].value
      self.data[data_name].append(value)
      assigns[data_name] = self.data[data_name][-1]

    value = self.relation().compute(assigns)
    self.ideal_mean.append(value)
    self.meas_mean.append(mean)
    self.meas_stdev.append(std)

  @property
  def size(self):
    return len(self.ideal_mean)

  @staticmethod
  def from_json(dev,data):
    blk = dev.get_block(data['block'])
    output = blk.outputs[data['output']]
    loc = devlib.Location.from_json(data['loc'])
    cfg = adplib.BlockConfig.from_json(dev,data['config'])
    method = llenums.ProfileOpType(data['method'])

    ds = ExpProfileDataset(blk,loc,output,cfg,method)

    for input_name in ds.inputs.keys():
      ds.inputs[input_name] = data['inputs'][input_name]

    for data_name in ds.data.keys():
      ds.data[data_name] = data['data'][data_name]

    ds.ideal_mean = data['ideal']
    ds.meas_mean = data['meas']['mean']
    ds.meas_stdev = data['meas']['stdev']


    return ds

  def to_json(self):
    return {
      'block': self.block.name,
      'loc':self.loc.to_json(),
      'config': self.config.to_json(),
      'output': self.output.name,
      'inputs': self.inputs,
      'method': self.method.value,
      'data': self.data,
      'ideal': self.ideal_mean,
      'meas': {
        'mean': self.meas_mean,
        'stdev': self.meas_stdev
      }
    }

  def __len__(self):
    return len(self.meas_mean)


  def __repr__(self):
    st = "%s %s %s [method=%s]\n" \
         % (self.block.name,self.loc,self.output.name,self.method.value)
    st += str(self.config)
    for idx in range(len(self)):
      inps = dict(map(lambda tup: (tup[0],tup[1][idx]), \
                      self.inputs.items()))
      dat = dict(map(lambda tup: (tup[0],tup[1][idx]), \
                      self.data.items()))

      out = self.ideal_mean[idx]
      meas = self.meas_mean[idx]
      st += "inps=%s dat=%s out=%s meas=%s\n" \
            % (inps,dat,out,meas)

    return st

def __to_datasets(dev,matches):
  for match in matches:
    try:
      yield ExpProfileDataset.from_json(dev, \
                                        runtime_util.decode_dict(match['dataset']))
    except Exception as e:
      print("dataset parse exception <%s>" % e)
      pass


class ExpProfileDatasetClause(Enum):
  BLOCK = "block"
  LOC = "loc"
  OUTPUT = "output"
  METHOD = "method"
  CALIB_OBJ = "calib_obj"
  STATIC_CONFIG = "static_config"
  HIDDEN_CONFIG = "hidden_config"

def _derive_where_clause(clauses,block,loc,output,cfg,method,calib_obj):
  def test_if_null(qty,msg):
    if qty is None:
      raise Exception(msg)

  where_clause = {}
  for clause in clauses:
    cls = ExpProfileDatasetClause(clause)
    if cls == ExpProfileDatasetClause.BLOCK:
      test_if_null(block, "get_models: expected block.")
      where_clause['block'] = block.name

    elif cls == ExpProfileDatasetClause.LOC:
      test_if_null(loc, "get_models: expected loc.")
      where_clause['loc'] = str(loc)

    elif cls == ExpProfileDatasetClause.OUTPUT:
      test_if_null(loc,"get_models: expected output")
      where_clause['output'] =output.name

    elif cls == ExpProfileDatasetClause.METHOD:
      test_if_null(loc,"get_models: expected method")
      where_clause['method'] =output.name

    elif cls == ExpProfileDatasetClause.STATIC_CONFIG:
      test_if_null(cfg,"get_models: expected config")
      where_clause['static_config'] =runtime_util.get_static_cfg(block,cfg)

    elif cls == ExpProfileDatasetClause.HIDDEN_CONFIG:
      test_if_null(cfg,"get_models: expected config")
      where_clause['hidden_config'] =runtime_util.get_hidden_cfg(block,cfg)

    elif cls == ExpProfileDatasetClause.CALIB_OBJ:
      test_if_null(calib_obj,"get_models: expected calibration objective")
      where_clause['calib_obj'] =calib_obj.value

    else:
      raise Exception("unknown??")

  return where_clause



def update(dev,dataset):
    assert(isinstance(dataset,ExpProfileDataset))
    #fields['phys_dataset'] = phys_util.encode_dict(fields['phys_dataset'])
    where_clause = {
      'block': dataset.block.name,
      'loc': str(dataset.loc),
      'output': dataset.output.name,
      'method':dataset.method.name,
      'static_config': dataset.static_cfg,
      'hidden_config': dataset.hidden_cfg
    }
    insert_clause = dict(where_clause)
    insert_clause['dataset'] = runtime_util.encode_dict(dataset.to_json())

    matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.PROFILE_DATASET, \
                                     where_clause))
    if len(matches) == 0:
      dev.physdb.insert(dblib.PhysicalDatabase.DB.PROFILE_DATASET,insert_clause)
    elif len(matches) == 1:
      dev.physdb.update(dblib.PhysicalDatabase.DB.PROFILE_DATASET, \
                        where_clause,insert_clause)

def load(dev,block,loc,output,cfg,method):
    where_clause = {
      'block': block.name,
      'loc': str(loc),
      'output':output.name,
      'method':method.name,
      'static_config': runtime_util.get_static_cfg(block,cfg),
      'hidden_config': runtime_util.get_hidden_cfg(block,cfg)
    }
    matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.PROFILE_DATASET,
                                     where_clause))
    if len(matches) == 1:
      return list(__to_datasets(dev,matches))[0]
    elif len(matches) == 0:
      pass
    else:
      raise Exception("can only have one match")

def get_configured_block_instances(dev):
  instances = {}
  for ds in get_all(dev):
    key = "%s-%s-%s-%s" % (ds.block.name,ds.loc, \
                           ds.static_cfg, \
                           ds.hidden_cfg)
    if not key in instances:
      instances[key] = (ds.block,ds.loc,ds.config)

  for blk,loc,cfg in instances.values():
    yield blk,loc,cfg

def get_all(dev):
     matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.PROFILE_DATASET, {}))
     return list(__to_datasets(dev,matches))

def remove_all(dev):
  where_clause = {}
  dev.physdb.delete(dblib.PhysicalDatabase.DB.PROFILE_DATASET, \
                    where_clause)


def get_datasets(dev,clauses,block=None,loc=None,output=None,config=None,method=None,calib_obj=None):
  where_clause = _derive_where_clause(clauses,block,loc,output,config,method,calib_obj)
  matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.PROFILE_DATASET, where_clause))
  datasets = list(__to_datasets(dev,matches))
  return datasets


def remove_datasets(dev,clauses,block=None,loc=None,output=None,config=None,method=None,calib_obj=None):
  where_clause = _derive_where_clause(clauses,block,loc,output,config,calib_obj)
  dev.physdb.delete(dblib.PhysicalDatabase.DB.PROFILE_DATASET, \
                    where_clause)



'''
def get_datasets_by_configured_block(dev,block,cfg, \
                                     hidden=True):
    where_clause = {
      'block': block.name,
      'static_config': runtime_util.get_static_cfg(block,cfg)
    }
    if hidden:
      where_clause['hidden_config'] = runtime_util.get_hidden_cfg(block,cfg)

    matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.PROFILE_DATASET,
                                     where_clause))

    return list(__to_datasets(dev,matches))


def get_datasets_by_configured_block_instance(dev,block,loc,output,cfg, \
                                              hidden=True):
    where_clause = {
      'block': block.name,
      'loc': str(loc),
      'output':output.name,
      'static_config': runtime_util.get_static_cfg(block,cfg),
    }
    if hidden:
      where_clause['hidden_config'] = runtime_util.get_hidden_cfg(block,cfg)

    matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.PROFILE_DATASET,
                                     where_clause))

    return list(__to_datasets(dev,matches))


def remove_all(dev):
  where_clause = {}
  dev.physdb.delete(dblib.PhysicalDatabase.DB.PROFILE_DATASET, \
                    where_clause)


'''
