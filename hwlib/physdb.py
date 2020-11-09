import sqlite3
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llenums as llenums
import ops.generic_op as ops
import base64
import json
import numpy as np
import phys_model.phys_util as phys_util
from enum import Enum

CREATE_DELTA_TABLE = '''
CREATE TABLE IF NOT EXISTS delta_models (
block text,
loc text,
output text,
static_config text,
hidden_config text,
config text,
dataset text,
delta_model text,
cost real,
primary key (block,loc,output,static_config,hidden_config)
);
'''
CREATE_PHYS_TABLE = '''
CREATE TABLE IF NOT EXISTS physical_models (
block text,
loc text,
output text,
static_config text,
phys_model text,
primary key (block,loc,output,static_config)
);
'''

def encode_dict(data):
  text = json.dumps(data)
  bytes_ = base64.b64encode(text.encode('utf-8')) \
                 .decode('utf-8')
  return bytes_

def decode_dict(data):
  text = base64.b64decode(data) \
               .decode('utf-8')
  return json.loads(text)

def dict_to_identifier(dict_):
  sorted_keys = sorted(dict_.keys())
  st = ""
  for k in sorted_keys:
    st += ";"
    st += "%s={%s}" % (k,dict_[k])

  return "[" + st[1:] + "]"

class PhysicalDatabase:
  class DB(Enum):
    DELTA_MODELS = "delta_models"
    PHYSICAL_MODELS = "physical_models"

  def __init__(self,board_name,path=""):
    self.board = board_name
    self.filename = path+"%s.db" % self.board
    self.conn = sqlite3.connect(self.filename)
    self.curs = self.conn.cursor()
    self.curs.execute(CREATE_PHYS_TABLE)
    self.curs.execute(CREATE_DELTA_TABLE)
    self.conn.commit()
    self.phys_keys = ['block','loc','output','static_config', \
                      'phys_model']
    self.delta_keys = ['block','loc','output','static_config','hidden_config', \
            'config','dataset','delta_model','cost']

  def insert(self,db,_fields):
    assert(isinstance(db,PhysicalDatabase.DB))
    if db == PhysicalDatabase.DB.DELTA_MODELS:
      INSERT = '''INSERT INTO {db} (block,loc,output,static_config,hidden_config,config,dataset,delta_model,cost)
      VALUES ('{block}','{loc}','{output}','{static_config}','{hidden_config}','{config}','{dataset}','{delta_model}',{cost});'''
    elif db == PhysicalDatabase.DB.PHYSICAL_MODELS:
      INSERT = '''INSERT INTO {db} (block,loc,output,static_config,phys_model)
      VALUES ('{block}','{loc}','{output}','{static_config}','{phys_model}');'''

    fields = dict(_fields)
    fields['db'] = db.value
    cmd = INSERT.format(**fields)
    self.curs.execute(cmd)
    self.conn.commit()

  def _where_clause(self,db,fields):
    assert(isinstance(db,PhysicalDatabase.DB))
    reqs = []
    keys = self.delta_keys if db == PhysicalDatabase.DB.DELTA_MODELS \
           else self.phys_keys
    where_clause = dict(filter(lambda tup: tup[0] in keys, \
                               fields.items()))
    for k,v in where_clause.items():
      reqs.append("%s='%s'" % (k,v.replace("'","''")))

    if len(reqs) > 0:
      return "WHERE "+(" AND ".join(reqs))
    else:
      return ""

  def update(self,db,where_clause,_fields):
    assert(isinstance(db,PhysicalDatabase.DB))
    where_clause_frag = self._where_clause(db,where_clause)
    assert(len(where_clause_frag) > 0)
    if db == PhysicalDatabase.DB.DELTA_MODELS:
      UPDATE = "UPDATE {db} SET dataset='{dataset}',delta_model='{delta_model}',cost={cost} "
    else:
      UPDATE = "UPDATE {db} SET phys_model='{phys_model}' "

    fields = dict(_fields)
    fields['db'] = db.value
    cmd = UPDATE.format(**fields) + where_clause_frag
    self.curs.execute(cmd)
    self.conn.commit()

  def _select(self,db,action_clause,where_clause,distinct=False):
    assert(isinstance(db,PhysicalDatabase.DB))
    where_clause_frag = self._where_clause(db,where_clause)
    if distinct:
      command = "SELECT DISTINCT"
    else:
      command = "SELECT"

    cmd_templ = "{command} {action} FROM {db} {where}"

    SELECT = cmd_templ.format(command=command, \
                              action=action_clause, \
                              db=db.value,
                              where=where_clause_frag)

    result = self.curs.execute(SELECT)
    for row in self.curs.fetchall():
      yield row

  def select(self,db,fields):
    assert(isinstance(db,PhysicalDatabase.DB))
    keys = self.delta_keys if db == PhysicalDatabase.DB.DELTA_MODELS \
           else self.phys_keys

    for row in self._select(db,"*",fields):
      yield dict(zip(keys,row))

  def select_field(self,db,field_names,where_clause):
    assert(isinstance(db,PhysicalDatabase.DB))
    keys = self.delta_keys if db == PhysicalDatabase.DB.DELTA_MODELS \
           else self.phys_keys

    for field_name in field_names:
      if not (field_name in keys):
        raise Exception("field <%s> not in database <%s>" % (field_name,db.value))

    select_clause = ",".join(field_names)
    for field_values in self._select(db, \
                                     select_clause, \
                                     where_clause,\
                                     distinct=True):
      yield dict(zip(field_names,field_values))




class ExpDataset:
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

class ExpPhysModel:

  def __init__(self,physmodelcoll,physical_model):
    assert(isinstance(physmodelcoll,ExpPhysModelCollection))
    assert(isinstance(physical_model,blocklib.PhysicalModelSpec))
    self.coll = physmodelcoll
    self.spec = physical_model
    assert(not self.spec is None)
    self.params = {}

  def predict(self,inputs):
    input_fields = list(inputs.keys())
    input_value_set = list(inputs.values())
    n = len(input_value_set[0])
    outputs = []
    params = dict(self.params)
    rel = self.spec.get_model(params)

    for values in zip(*input_value_set):
      inp_map = dict(list(zip(input_fields,values)) + \
                     list(params.items()))
      output = rel.compute(inp_map)
      outputs.append(output)

    return outputs


  def concrete_relation(self):
    assert(self.complete)
    assigns = dict(map(lambda tup: (tup[0],ops.Const(tup[1])), \
                       self.params.items()))
    return self.spec.relation.substitute(assigns)

  def bind(self,par,value):
    assert(not par in self.params)
    if not (par in self.spec.params):
      print("WARN: couldn't bind nonexistant parameter <%s> in phys (%s)" % \
            (par,self.spec.params))
      return

    self.params[par] = value
    self.coll.update()

  def to_json(self):
    return self.params

  def update(self,json):
    for par,value in json.items():
      self.bind(par,value)

  @property
  def complete(self):
    for par in self.spec.params:
      if not par in self.params:
        return False
    return True

  def clear(self):
    self.params = {}
    self.cost = ExpDeltaModel.MAX_COST

  def bind(self,par,value):
    if not (par in self.spec.params):
      print("WARN: couldn't bind nonexistant parameter <%s> in delta" % par)
      return

    self.params[par] = value

  def __repr__(self):
    return str(self.params) + " / " + str(self.spec)

class ExpPhysModelCollection:
  def __init__(self,physblk):
    self.phys = physblk
    self.delta_model = self.phys.output \
                                .deltas[self.phys.cfg.mode]

    self._delta_params = {}
    for par in self.delta_model.params:
      if not self.delta_model[par].model is None:
        self._delta_params[par] = ExpPhysModel(self, \
                                               self.delta_model[par].model)

    if not self.delta_model.model_error is None:
      self.model_error = ExpPhysModel(self, \
                                      self.delta_model.model_error)


  @property
  def complete(self):
    for v in self._delta_params.values():
      if not v.complete:
        return False
    return self.model_error.complete

  def clear(self):
    self.model_error.clear()
    for v in self._delta_params.values():
      v.clear()

  @property
  def delta_model_params(self):
    for p,v in self._delta_params.items():
      yield p,v

  def to_json(self):
    delta_pars = dict(map(lambda tup: (tup[0],tup[1].to_json()),  \
                          self._delta_params.items()))
    return {
      'delta_params': delta_pars,
      'model_error': self.model_error.to_json()
    }


  @staticmethod
  def from_json(physcfg,obj):
    cfg = ExpPhysModelCollection(physcfg)
    cfg.model_error.update(obj['model_error'])
    for par,subobj in obj['delta_params'].items():
      cfg._delta_params[par].update(subobj)
    return cfg

  def update(self):
    self.phys.update()

  def __getitem__(self,v):
    return self._delta_params[v]

  def __repr__(self):
    st = ""
    for par,model in self._delta_params.items():
      st += "par %s = %s\n" % (par,model)

    st += "model-error = %s\n" % (self.model_error)
    return st

class ExpDeltaModel:
  MAX_COST = 9999

  def __init__(self,physblk):
    self.phys = physblk
    self.spec = self.phys.output \
                                .deltas[self.phys.cfg.mode]
    self.params = {}
    self.cost = ExpDeltaModel.MAX_COST

  @property
  def complete(self):
    for par in self.spec.params:
      if not par in self.params:
        return False
    return True

  def clear(self):
    self.params = {}
    self.cost = ExpDeltaModel.MAX_COST

  def bind(self,par,value):
    assert(not par in self.params)
    if not (par in self.spec.params):
      print("WARN: couldn't bind nonexistant parameter <%s> in delta" % par)
      return

    self.params[par] = value

  def error(self,inputs,meas_outputs):
    pred_outputs = self.predict(inputs)
    cost = 0
    n = 0
    for pred,meas in zip(pred_outputs,meas_outputs):
      cost += pow(pred-meas,2)
      n += 1

    return np.sqrt(cost/n)

  def predict(self,inputs,correctable_only=False):
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
    model.cost = obj['cost']
    return model

  def to_json(self):
    return {
      'params': self.params,
      'cost': self.cost
    }

class ExpCfgBlock:

  def __init__(self,db,blk,loc,out_port,blkcfg, \
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
    self.delta_model = ExpDeltaModel(self)
    self.phys_models = ExpPhysModelCollection(self)

    self.status_type = status_type
    self.method_type = method_type
    self.dataset = ExpDataset(self)
    self.load()

  # combinatorial block config (modes) and calibration codes
  @staticmethod
  def get_hidden_cfg(block,cfg,exclude=[]):
    mode = cfg.mode
    kvs = {}
    for stmt in cfg.stmts:
      if stmt.type == adplib.ConfigStmtType.STATE and \
         isinstance(block.state[stmt.name].impl, \
                        blocklib.BCCalibImpl) and \
                        not stmt.name in exclude:
        assert(not stmt.name in kvs)
        kvs[stmt.name] = stmt.type.value+" "+stmt.pretty_print()

    return dict_to_identifier(kvs)

  def hidden_codes(self):
    for stmt in self.cfg.stmts:
      if stmt.type == adplib.ConfigStmtType.STATE and \
         isinstance(self.block.state[stmt.name].impl, \
                    blocklib.BCCalibImpl):
        yield stmt.name,stmt.value

  @staticmethod
  def get_static_cfg(block,cfg):
    mode = cfg.mode
    kvs = {}
    kvs['mode'] = mode
    for stmt in cfg.stmts:
      if stmt.type == adplib.ConfigStmtType.STATE and \
         not isinstance(block.state[stmt.name].impl, \
                        blocklib.BCCalibImpl):
        assert(not stmt.name in kvs)
        kvs[stmt.name] = stmt.t.value+" "+stmt.pretty_print()

    return dict_to_identifier(kvs)

  @staticmethod
  def get_dynamic_cfg(cfg):
    kvs = {}
    for stmt in cfg.stmts:
      if stmt.type == adplib.ConfigStmtType.CONSTANT:
        assert(not stmt.name in kvs)
        kvs[stmt.name] = stmt.value
    return kvs

  @property
  def hidden_cfg(self):
    return ExpCfgBlock.get_hidden_cfg(self.block, \
                                       self.cfg)


  @property
  def static_cfg(self):
    return ExpCfgBlock.get_static_cfg(self.block, \
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
      'phys_model': self.phys_models.to_json(),
      'cost':self.delta_model.cost
    }

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
    fields['config'] = encode_dict(fields['config'])
    fields['dataset'] = encode_dict(fields['dataset'])
    fields['delta_model'] = encode_dict(fields['delta_model'])
    fields['phys_model'] = encode_dict(fields['phys_model'])
    where_clause = {
      'block': self.block.name,
      'loc': str(self.loc),
      'output': self.output.name,
      'static_config': self.static_cfg,
      'hidden_config': self.hidden_cfg,
    }
    matches = list(self.db.select(PhysicalDatabase.DB.DELTA_MODELS,where_clause))
    if len(matches) == 0:
      self.db.insert(PhysicalDatabase.DB.DELTA_MODELS,fields)
    elif len(matches) == 1:
      self.db.update(PhysicalDatabase.DB.DELTA_MODELS, \
                     where_clause,fields)

    matches = list(self.db.select(PhysicalDatabase.DB.PHYSICAL_MODELS,where_clause))
    if len(matches) == 0:
      self.db.insert(PhysicalDatabase.DB.PHYSICAL_MODELS,fields)
    elif len(matches) == 1:
      self.db.update(PhysicalDatabase.DB.PHYSICAL_MODELS, \
                     where_clause,fields)


  def load(self):
    where_clause = {
      'block': self.block.name,
      'loc': str(self.loc),
      'output':self.output.name,
      'static_config': self.static_cfg,
      'hidden_config': self.hidden_cfg
    }
    matches = list(self.db.select(PhysicalDatabase.DB.DELTA_MODELS,
                                  where_clause))
    if len(matches) == 1:
      json_dataset = decode_dict(matches[0]['dataset'])
      self.dataset = ExpDataset.from_json(self,json_dataset)
      json_delta_model = decode_dict(matches[0]['delta_model'])
      self.delta_model = ExpDeltaModel.from_json(self,json_delta_model)
    elif len(matches) == 0:
      pass
    else:
      raise Exception("can only have one match")

    matches = list(self.db.select(PhysicalDatabase.DB.PHYSICAL_MODELS,
                                  where_clause))
    if len(matches) == 1:
      json_physical_model = decode_dict(matches[0]['phys_model'])
      self.phys_models = ExpPhysModelCollection \
          .from_json(self,json_physical_model)
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
    assert(isinstance(db,PhysicalDatabase))
    assert(isinstance(dev,devlib.Device))
    blk = dev.get_block(obj['block'])
    loc = devlib.Location.from_string(obj['loc'])
    output = blk.outputs[obj['output']]
    cfg_obj = decode_dict(obj['config'])
    cfg = adplib.BlockConfig.from_json(dev,cfg_obj)
    phys = ExpCfgBlock(db,blk,loc,output,cfg, \
                        dev.profile_status_type, \
                        dev.profile_op_type)
    json_dataset = decode_dict(obj['dataset'])
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

def get_best_configured_physical_block(db,dev,blk,inst,cfg):
  static_cfg = ExpCfgBlock.get_static_cfg(blk,cfg)
  where_clause = {'block':blk.name, \
                  'loc':str(inst), \
                  'static_config':static_cfg}

  by_hidden_cfg = {}
  hidden_cfg_costs = {}
  # compute costs
  for row in db.select(where_clause):
    phys = ExpCfgBlock.from_json(db,dev,row)
    if not phys.hidden_cfg in by_hidden_cfg:
      by_hidden_cfg[phys.hidden_cfg] = []

    by_hidden_cfg[phys.hidden_cfg].append(phys)

  best_hidden_cfg = None
  best_cost = None
  for hidden_cfg,physblocks in by_hidden_cfg.items():
    cost = max(map(lambda blk: blk.model.cost, physblocks))
    if best_hidden_cfg is None or best_cost > cost:
      best_hidden_cfg = hidden_cfg
      best_cost = cost

  assert(not best_hidden_cfg is None)
  for physblk in by_hidden_cfg[best_hidden_cfg]:
    yield physblk

def get_by_block_instance(db,dev,blk,inst,cfg=None,hidden=False):
  where_clause = {'block':blk.name, \
                  'loc':str(inst) \
  }

  if not cfg is None:
    static_cfg = ExpCfgBlock.get_static_cfg(blk,cfg)
    where_clause['static_config'] = static_cfg
    if hidden:
      hidden_cfg = PhysCfgBlock.get_hidden_cfg(blk,cfg)
      where_clause['hidden_config'] = hidden_cfg


  for row in db.select(PhysicalDatabase.DB.DELTA_MODELS, where_clause):
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

  for row in db.select(PhysicalDatabase.DB.DELTA_MODELS, where_clause):
    return ExpCfgBlock.from_json(db,dev,row).phys_models


