import hwlib.hcdc.llenums as llenums

import hwlib.block as blocklib
import hwlib.device as devlib
import hwlib.adp as adplib

import runtime.runtime_util as runtime_util
import runtime.models.database as dblib
import ops.generic_op as genoplib
import ops.op as oplib


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



  def relation(self):
      rel = self.output.relation[self.config.mode]
      if runtime_util.is_integration_op(rel):
          if self.method == llenums.ProfileOpType.INTEG_INITIAL_COND:
              return rel.init_cond
          elif self.method == llenums.ProfileOpType.INTEG_DERIVATIVE_GAIN:
              return genoplib.Const(1.0)
          else:
              return genoplib.Const(0.0)
      else:
          return rel




  def get_data(self,method):
    def valid_data_point(idx):
      return self.meas_method[idx] == method

    indices = list(filter(lambda idx: valid_data_point(idx), \
                          range(0,self.size)))
    valid_inputs = {}
    for inp in self.inputs:
      assert(not inp in valid_inputs)
      valid_inputs[inp] = runtime_util.get_subarray(self.inputs[inp], \
                                               indices)

    for data_field in self.data:
      assert(not data_field in valid_inputs)
      valid_inputs[data_field] = runtime_util.get_subarray(self.data[data_field], \
                                                      indices)

    return {
      "inputs":valid_inputs,
      "ideal_mean":runtime_util.get_subarray(self.ideal_mean,indices),
      "meas_mean":runtime_util.get_subarray(self.meas_mean,indices),
      "meas_stdev":runtime_util.get_subarray(self.meas_stdev,indices)
    }

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
    return len(self.output)

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
      'config': self.cfg.to_json(),
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



def __to_datasets(dev,matches):
  for match in matches:
    yield ExpProfileDataset.from_json(dev, \
                                      runtime_util.decode_dict(match['dataset']))

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

def get_datasets(dev):
     matches = list(dev.physdb.select(dblib.PhysicalDatabase.DB.PROFILE_DATASET, {}))
     return list(__to_datasets(dev,matches))
 
