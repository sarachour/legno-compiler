import hwlib.physdb as physdb
import hwlib.physdb_util as physutil
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib

import hwlib.hcdc.llenums as llenums
import ops.op as oplib
import ops.generic_op as genoplib

class ExpDataset:

  def _populate_integral_operation(self):
    expr = self.relation[llenums.ProfileOpType.INPUT_OUTPUT]
    if expr.op == oplib.OpType.INTEG:
      self.relation[llenums.ProfileOpType.INTEG_INITIAL_COND] = expr.init_cond
      self.relation[llenums.ProfileOpType.INTEG_DERIVATIVE_GAIN] = genoplib.Const(1.0)
      self.relation[llenums.ProfileOpType.INTEG_DERIVATIVE_BIAS] = genoplib.Const(0.0)
      self.relation[llenums.ProfileOpType.INTEG_DERIVATIVE_STABLE] = genoplib.Const(0.0)



  def __init__(self,physblk):
    assert(isinstance(physblk, ExpCfgBlock))
    self.phys = physblk

    # inputs
    self._port_map = {}
    self.relation = {}
    self.data = {}
    self.inputs = {}
    self.output = []
    self.meas_mean = []
    self.meas_stdev = []
    self.meas_method = []
    self.meas_status = []

    self.output_port = self.phys.output
    self.mode = self.phys.cfg.mode

    self.relation[llenums.ProfileOpType.INPUT_OUTPUT]  \
      = self.output_port.relation[self.mode]

    self._populate_integral_operation()

    variables = self.relation[llenums.ProfileOpType.INPUT_OUTPUT].vars()
    for input_port in self.phys.block.inputs:
      if input_port.name in variables:
        self.inputs[input_port.name] = []

    for stmt in self.phys.cfg.stmts:
      if stmt.type == adplib.ConfigStmtType.CONSTANT:
        self.data[stmt.name] = []

    assigned = list(self.inputs.keys()) + list(self.data.keys())
    for v in variables:
      if not v in assigned:
        raise Exception("unknown variable: %s" % v)

  def __len__(self):
    return len(self.output)

  def get_data(self,status,method):
    def valid_data_point(idx):
      return self.meas_status[idx] == status \
        and self.meas_method[idx] == method

    indices = list(filter(lambda idx: valid_data_point(idx), \
                          range(0,self.size)))
    all_inputs = {}
    for inp in self.inputs:
      assert(not inp in all_inputs)
      all_inputs[inp] = phys_util.get_subarray(self.inputs[inp], \
                                               indices)

    for data_field in self.data:
      assert(not data_field in all_inputs)
      all_inputs[data_field] = phys_util.get_subarray(self.data[data_field], \
                                                      indices)

    return {
      "inputs":all_inputs,
      "outputs":phys_util.get_subarray(self.output,indices),
      "meas_mean":phys_util.get_subarray(self.meas_mean,indices),
      "meas_stdev":phys_util.get_subarray(self.meas_stdev,indices)
    }

  def add(self,method,inputs,dynamic_codes,status,mean,std):
    var_assigns = {}
    for in_port,in_val in inputs.items():
      var_assigns[in_port] = in_val

    for data_port,data_val in dynamic_codes.items():
      var_assigns[data_port] = data_val

    value = self.relation[method].compute(var_assigns)
    self.meas_mean.append(mean)
    self.meas_stdev.append(std)
    assert(isinstance(status,self.phys.status_type))
    self.meas_status.append(status)
    assert(isinstance(method,self.phys.method_type))
    self.meas_method.append(method)
    self.output.append(value)

    for input_name in self.inputs.keys():
      self.inputs[input_name].append(inputs[input_name])
    for data_name in self.data.keys():
      self.data[data_name].append(dynamic_codes[data_name])

  @property
  def size(self):
    return len(self.output)

  @staticmethod
  def from_json(physblk,data):
    ds = ExpDataset(physblk)
    for input_name in ds.inputs.keys():
      ds.inputs[input_name] = data['inputs'][input_name]

    for data_name in ds.data.keys():
      ds.data[data_name] = data['data'][data_name]

    ds.output = data['output']
    ds.meas_mean = data['meas']['mean']
    ds.meas_stdev = data['meas']['stdev']
    ds.meas_status = list(map(lambda val: physblk.status_type(val), \
                              data['meas']['status']))
    ds.meas_method = list(map(lambda val: physblk.method_type(val), \
                              data['meas']['method']))


    return ds

  def to_json(self):
    return {
      'inputs': self.inputs,
      'data': self.data,
      'output': self.output,
      'meas': {
        'mean': self.meas_mean,
        'stdev': self.meas_stdev,
        'method': list(map(lambda v: v.value, self.meas_method)),
        'status': list(map(lambda v: v.value, self.meas_status))
      }
    }

class ExpDeltaModel:
  MAX_MODEL_ERROR = 9999

  def __init__(self,physblk):
    self.phys = physblk
    self.spec = self.phys.output \
                         .deltas[self.phys.cfg.mode]
    self.params = {}
    self.model_error = ExpDeltaModel.MAX_MODEL_ERROR
    self.label = physutil.DeltaModelLabel.NONE

  @property
  def complete(self):
    for par in self.spec.params:
      if not par in self.params:
        return False
    return True

  def clear(self):
    self.params = {}
    self.model_error = ExpDeltaModel.MAX_MODEL_ERROR

  def bind(self,par,value):
    assert(not par in self.params)
    if not (par in self.spec.params):
      print("WARN: couldn't bind nonexistant parameter <%s> in delta" % par)
      return

    self.params[par] = value

  def error(self,inputs,meas_outputs,init_cond=False):
    pred_outputs = self.predict(inputs, \
                                init_cond=init_cond)
    model_error = 0
    n = 0
    for pred,meas in zip(pred_outputs,meas_outputs):
      model_error += pow(pred-meas,2)
      n += 1

    return np.sqrt(model_error/n)


  def predict(self,inputs, \
              init_cond=False,
              correctable_only=False):
    input_fields = list(inputs.keys())
    input_value_set = list(inputs.values())
    n = len(input_value_set[0])
    outputs = []
    params = dict(self.params)

    if correctable_only:
      rel = self.spec.get_correctable_model(params)
    else:
      rel = self.spec.get_model(params)

    for values in zip(*input_value_set):
      inp_map = dict(list(zip(input_fields,values)) + \
                     list(params.items()))
      if rel.op == oplib.OpType.INTEG:
        if init_cond:
          output = rel.init_cond.compute(inp_map)
        else:
          output = rel.deriv.compute(inp_map)
      else:
        output = rel.compute(inp_map)
      outputs.append(output)

    return outputs

  @staticmethod
  def from_json(physcfg,obj):
    model = ExpDeltaModel(physcfg)
    if obj is None:
      return model

    for par,value in obj['params'].items():
      model.bind(par,value)
    model.model_error = obj['model_error']
    model.label = physutil.DeltaModelLabel(obj['label'])
    return model

  def to_json(self):
    return {
      'params': self.params,
      'model_error': self.model_error,
      'label':self.label.value
    }

  def __repr__(self):
    return "empirical-delta-model(%s,model_err=%s) :%s" % (self.params, \
                                           self.model_error, \
                                           self.label.value)



class ExpCfgBlock:

  def __init__(self,db,dev,blk,loc,out_port,blkcfg, \
               status_type,method_type):
    assert(isinstance(blkcfg,adplib.BlockConfig))
    assert(isinstance(blk,blocklib.Block))
    assert(isinstance(loc,devlib.Location))
    assert(isinstance(out_port,blocklib.BlockOutput))
    assert(blkcfg.complete())
    self.block = blk
    self.loc = loc
    self.output = out_port
    self.cfg = blkcfg
    self.db = db
    self.dev = dev
    self.delta_model = ExpDeltaModel(self)
    #self.phys_models = ExpPhysModelCollection(self)

    self.status_type = status_type
    self.method_type = method_type
    self.dataset = ExpDataset(self)
    self.load()

  def hidden_codes(self):
    for stmt in self.cfg.stmts:
      if stmt.type == adplib.ConfigStmtType.STATE and \
         isinstance(self.block.state[stmt.name].impl, \
                    blocklib.BCCalibImpl):
        yield stmt.name,stmt.value

  @property
  def hidden_cfg(self):
    return physutil.get_hidden_cfg(self.block, \
                                       self.cfg)


  @property
  def static_cfg(self):
    return physutil.get_static_cfg(self.block, \
    self.cfg)

  # dynamic values (data)
  def dynamic_cfg(self):
    pass

  def to_json(self):
    return {
      'block': self.block.name,
      'loc': str(self.loc),
      'output': self.output.name,
      'static_config': self.static_cfg,
      'hidden_config': self.hidden_cfg,
      'config': self.cfg.to_json(),
      'dataset':self.dataset.to_json(),
      'delta_model': self.delta_model.to_json(),
      'model_error':self.delta_model.model_error
    }
  #'phys_model': self.phys_models.to_json(),

  def get_bounds(self):
    bounds = {}
    for inp in self.block.inputs:
      ival = inp.interval[self.cfg.mode]
      if ival is None:
        raise Exception("no interval for input %s.<%s> in mode <%s>" \
                        % (self.block.name,inp.name,self.cfg.mode))
      bounds[inp.name] = [ival.lower,ival.upper]

    for dat in self.block.data:
      ival = dat.interval[self.cfg.mode]
      if ival is None:
        raise Exception("no interval for datum %s.<%s> in mode <%s>" \
                        % (self.block.name,dat.name,self.cfg.mode))
      bounds[dat.name] = [ival.lower,ival.upper]

    for out in self.block.outputs:
      ival = out.interval[self.cfg.mode]
      if ival is None:
        raise Exception("no interval for output %s.<%s> in mode <%s>" \
                        % (self.block.name,out.name,self.cfg.mode))

      bounds[out.name] = [ival.lower,ival.upper]

    return bounds

  def update(self):
    fields = self.to_json()
    fields['config'] = physutil.encode_dict(fields['config'])
    fields['dataset'] = physutil.encode_dict(fields['dataset'])
    fields['delta_model'] = physutil.encode_dict(fields['delta_model'])
    fields['label'] = self.delta_model.label.value
    #fields['phys_model'] = phys_util.encode_dict(fields['phys_model'])
    where_clause = {
      'block': self.block.name,
      'loc': str(self.loc),
      'output': self.output.name,
      'static_config': self.static_cfg,
      'hidden_config': self.hidden_cfg
    }

    matches = list(self.db.select(physdb.PhysicalDatabase.DB.DELTA_MODELS,where_clause))
    if len(matches) == 0:
      self.db.insert(physdb.PhysicalDatabase.DB.DELTA_MODELS,fields)
    elif len(matches) == 1:
      self.db.update(physdb.PhysicalDatabase.DB.DELTA_MODELS, \
                     where_clause,fields)

  def load(self):
    where_clause = {
      'block': self.block.name,
      'loc': str(self.loc),
      'output':self.output.name,
      'static_config': self.static_cfg,
      'hidden_config': self.hidden_cfg
    }
    matches = list(self.db.select(physdb.PhysicalDatabase.DB.DELTA_MODELS,
                                  where_clause))
    if len(matches) == 1:
      json_dataset = physutil.decode_dict(matches[0]['dataset'])
      self.dataset = ExpDataset.from_json(self,json_dataset)
      json_delta_model = physutil.decode_dict(matches[0]['delta_model'])
      self.delta_model = ExpDeltaModel.from_json(self,json_delta_model)
    elif len(matches) == 0:
      pass
    else:
      raise Exception("can only have one match")

  def add_datapoint(self,cfg,inputs,method,status,mean,std):
    # test that this is the same block usage
    assert(self.static_cfg  \
           == ExpCfgBlock.get_static_cfg(self.block,cfg))
    assert(self.cfg.inst == cfg.inst)
    assert(self.hidden_cfg  \
           == ExpCfgBlock.get_hidden_cfg(self.block,cfg))

    # add point
    self.dataset.add(method,inputs, \
                     ExpCfgBlock.get_dynamic_cfg(cfg), \
                     status, \
                     mean,std)
    self.update()

  @staticmethod
  def from_json(db,dev,obj):
    assert(isinstance(db,physdb.PhysicalDatabase))
    assert(isinstance(dev,devlib.Device))
    blk = dev.get_block(obj['block'])
    loc = devlib.Location.from_string(obj['loc'])
    output = blk.outputs[obj['output']]
    cfg_obj = physutil.decode_dict(obj['config'])
    cfg = adplib.BlockConfig.from_json(dev,cfg_obj)
    phys = ExpCfgBlock(db,dev, \
                       blk,loc,output,cfg, \
                       dev.profile_status_type, \
                       dev.profile_op_type)
    json_dataset = physutil.decode_dict(obj['dataset'])
    phys.dataset = ExpDataset.from_json(phys,json_dataset)
    return phys



def get_hidden_states(db,dev,blk,inst,st):
  where_clause = {'block':blk.name,
                  'loc':str(inst),
                  'static_config':st}
  cfgs = {}
  for fields in db.select_field(["hidden_config"],where_clause):
    hidden_cfg = fields["hidden_config"]
    cfgs[str(hidden_cfg)] = hidden_cfg
  return cfgs.values()


def get_static_states(db,dev,blk,inst):
  where_clause = {'block':blk.name,'loc':str(inst)}
  cfgs = {}
  for fields in db.select_field(["static_config"],where_clause):
    static_cfg = fields["static_config"]
    cfgs[str(static_cfg)] = static_cfg
  return cfgs.values()

def get_instances(db,dev,blk):
  where_clause = {'block':blk.name}
  insts = {}
  for fields in db.select_field(["loc"],where_clause):
    location = devlib.Location.from_string(fields["loc"])
    insts[str(location)] = location
  return insts.values()


def get_blocks(db,dev):
  where_clause = {}
  blocks = {}
  for fields in db.select_field(["block"],where_clause):
    block = dev.get_block(fields["block"])
    blocks[block.name] = block

  return blocks.values()
