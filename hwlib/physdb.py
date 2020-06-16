import sqlite3
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llenums as llenums
import ops.generic_op as ops
import base64
import json
import numpy as np

CREATE_TABLE = '''
CREATE TABLE IF NOT EXISTS physical (
block text,
loc text,
output text,
static_config text,
hidden_config text,
config text,
dataset text,
model text,
cost real,
primary key (block,loc,output,static_config,hidden_config)
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

  def __init__(self,board_name):
    self.board = board_name
    self.filename = "%s.db" % self.board
    self.conn = sqlite3.connect(self.filename)
    self.curs = self.conn.cursor()
    self.curs.execute(CREATE_TABLE)
    self.keys = ['block','loc','output','static_config','hidden_config', \
            'config','dataset','model','cost']
    self.conn.commit()

  def insert(self,fields):
    INSERT = '''INSERT INTO physical (block,loc,output,static_config,hidden_config,config,dataset,model,cost)
                VALUES ('{block}','{loc}','{output}','{static_config}','{hidden_config}','{config}','{dataset}','{model}',{cost});'''
    cmd = INSERT.format(**fields)
    self.curs.execute(cmd)
    self.conn.commit()

  def _where_clause(self,where_clause):
    reqs = []
    for k,v in where_clause.items():
      reqs.append("%s='%s'" % (k,v.replace("'","''")))

    if len(reqs) > 0:
      return "WHERE "+(" AND ".join(reqs))
    else:
      return ""

  def update(self,where_clause,fields):
    where_clause_frag = self._where_clause(where_clause)
    assert(len(where_clause_frag) > 0)
    UPDATE = "UPDATE physical SET dataset='{dataset}',model='{model}',cost={cost} "
    cmd = UPDATE.format(**fields) + where_clause_frag
    self.curs.execute(cmd)
    self.conn.commit()

  def _select(self,action_clause,where_clause):
    where_clause_frag = self._where_clause(where_clause)

    SELECT = "SELECT %s FROM physical %s" % (action_clause, \
                                             where_clause_frag)

    result = self.curs.execute(SELECT)
    for row in self.curs.fetchall():
      yield dict(zip(self.keys,row))


  def select(self,where_clause):
    return self._select("*",where_clause)




class PhysDataset:

  def __init__(self,physblk):
    assert(isinstance(physblk, PhysCfgBlock))
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
      if stmt.t == adplib.ConfigStmtType.CONSTANT:
        self.data[stmt.name] = []

    assigned = list(self.inputs.keys()) + list(self.data.keys())
    for v in variables:
      if not v in assigned:
        raise Exception("unknown variable: %s" % v)

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
    ds = PhysDataset(physblk)
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

class PhysDeltaModel:
  MAX_COST = 9999
  def __init__(self,physblk):
    self.phys = physblk
    self.delta_model = self.phys.output \
                                .deltas[self.phys.cfg.mode]
    self.params = {}
    self.cost = PhysDeltaModel.MAX_COST

  @property
  def complete(self):
    for par in self.delta_model.params:
      if not par in self.params:
        return False
    return True

  def bind(self,par,value):
    assert(not par in self.params)
    assert(par in self.delta_model.params)
    self.params[par] = value

  def error(self,inputs,meas_outputs):
    pred_outputs = self.predict(inputs)
    cost = 0
    n = 0
    for pred,meas in zip(pred_outputs,meas_outputs):
      cost += pow(pred-meas,2)
      n += 1

    return np.sqrt(cost/n)

  def predict(self,inputs):
    input_fields = list(inputs.keys())
    input_value_set = list(inputs.values())
    n = len(input_value_set[0])
    outputs = []
    for values in zip(*input_value_set):
      inp_map = dict(list(zip(input_fields,values)) + \
                     list(self.params.items()))
      output = self.delta_model.relation.compute(inp_map)
      outputs.append(output)

    return outputs

  @staticmethod
  def from_json(physcfg,obj):
    model = PhysDeltaModel(physcfg)
    for par,value in obj['params'].items():
      model.bind(par,value)
    model.cost = obj['cost']
    return model

  def to_json(self):
    return {
      'params': self.params,
      'cost': self.cost
    }

class PhysCfgBlock:

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
    self.model = PhysDeltaModel(self)

    self.status_type = status_type
    self.method_type = method_type
    self.dataset = PhysDataset(self)
    self.load()

  # combinatorial block config (modes) and calibration codes
  @staticmethod
  def get_hidden_cfg(block,cfg):
    mode = cfg.mode
    kvs = {}
    for stmt in cfg.stmts:
      if stmt.t == adplib.ConfigStmtType.STATE and \
         isinstance(block.state[stmt.name].impl, \
                        blocklib.BCCalibImpl):
        assert(not stmt.name in kvs)
        kvs[stmt.name] = stmt.t.value+" "+stmt.pretty_print()

    return dict_to_identifier(kvs)


  @staticmethod
  def get_static_cfg(block,cfg):
    mode = cfg.mode
    kvs = {}
    kvs['mode'] = mode
    for stmt in cfg.stmts:
      if stmt.t == adplib.ConfigStmtType.STATE and \
         not isinstance(block.state[stmt.name].impl, \
                        blocklib.BCCalibImpl):
        assert(not stmt.name in kvs)
        kvs[stmt.name] = stmt.t.value+" "+stmt.pretty_print()

    return dict_to_identifier(kvs)

  @staticmethod
  def get_dynamic_cfg(cfg):
    kvs = {}
    for stmt in cfg.stmts:
      if stmt.t == adplib.ConfigStmtType.CONSTANT:
        assert(not stmt.name in kvs)
        kvs[stmt.name] = stmt.value
    return kvs

  @property
  def hidden_cfg(self):
    return PhysCfgBlock.get_hidden_cfg(self.block,self.cfg)


  @property
  def static_cfg(self):
    return PhysCfgBlock.get_static_cfg(self.block,self.cfg)

  # dynamic values (data)
  def dynamic_cfg(self):
    pass

  def update(self):
    fields = {
      'block': self.block.name,
      'loc': str(self.loc),
      'output': self.output.name,
      'static_config': self.static_cfg,
      'hidden_config': self.hidden_cfg,
      'config': encode_dict(self.cfg.to_json()),
      'dataset':encode_dict(self.dataset.to_json()),
      'model': encode_dict(self.model.to_json()),
      'cost':self.model.cost
    }
    where_clause = {
      'block': self.block.name,
      'loc': str(self.loc),
      'output': self.output.name,
      'static_config': self.static_cfg,
      'hidden_config': self.hidden_cfg,
    }
    matches = list(self.db.select(where_clause))
    if len(matches) == 0:
      self.db.insert(fields)
    elif len(matches) == 1:
      self.db.update(where_clause,fields)

  def load(self):
    where_clause = {
      'block': self.block.name,
      'loc': str(self.loc),
      'output':self.output.name,
      'static_config': self.static_cfg,
      'hidden_config': self.hidden_cfg
    }
    matches = list(self.db.select(where_clause))
    if len(matches) == 1:
      json_dataset = decode_dict(matches[0]['dataset'])
      self.dataset = PhysDataset.from_json(self,json_dataset)
      json_model = decode_dict(matches[0]['model'])
      self.model = PhysDeltaModel.from_json(self,json_model)
    elif len(matches) == 0:
      return
    else:
      raise Exception("can only have one match")

  def add_datapoint(self,cfg,inputs,method,status,mean,std):
    # test that this is the same block usage
    assert(self.static_cfg  \
           == PhysCfgBlock.get_static_cfg(self.block,cfg))
    assert(self.cfg.inst == cfg.inst)
    assert(self.hidden_cfg  \
           == PhysCfgBlock.get_hidden_cfg(self.block,cfg))

    # add point
    self.dataset.add(method,inputs, \
                     PhysCfgBlock.get_dynamic_cfg(cfg), \
                     status, \
                     mean,std)
    self.update()

  @staticmethod
  def from_json(db,dev,obj):
    assert(isinstance(db,PhysicalDatabase))
    assert(isinstance(dev,devlib.Device))
    blk = dev.get_block(obj['block'])
    loc = devlib.Location(obj['loc'])
    output = blk.outputs[obj['output']]
    cfg_obj = decode_dict(obj['config'])
    cfg = adplib.BlockConfig.from_json(dev,cfg_obj)
    phys = PhysCfgBlock(db,blk,loc,output,cfg, \
                        dev.profile_status_type, \
                        dev.profile_op_type)
    json_dataset = decode_dict(obj['dataset'])
    phys.dataset = PhysDataset.from_json(phys,json_dataset)
    return phys





def get_best_calibrated_block(db,dev,blk,inst,cfg):
  static_cfg = PhysCfgBlock.get_static_cfg(blk,cfg)
  where_clause = {'block':blk.name, \
                  'loc':str(inst), \
                  'static_config':static_cfg}

  by_hidden_cfg = {}
  hidden_cfg_costs = {}
  # compute costs
  for row in db.select(where_clause):
    phys = PhysCfgBlock.from_json(db,dev,row)
    if not phys.hidden_cfg in by_hidden_cfg:
      by_hidden_cfg[phys.hidden_cfg] = []

    by_hidden_cfg[phys.hidden_cfg].append(phys)

  best_hidden_cfg = None
  best_cost = None
  for hidden_cfg,physblocks in by_hidden_cfg.items():
    cost = max(map(lambda blk: blk.model.cost, physblocks))
    print(cost)
    if best_hidden_cfg is None or best_cost > cost:
      best_hidden_cfg = hidden_cfg
      best_cost = cost

  assert(not best_hidden_cfg is None)
  for physblk in by_hidden_cfg[best_hidden_cfg]:
    yield physblk

def get_all_calibrated_blocks(db,dev,blk,inst,cfg):
  static_cfg = PhysCfgBlock.get_static_cfg(blk,cfg)
  where_clause = {'block':blk.name, \
                  'loc':str(inst), \
                  'static_config':static_cfg}

  for row in db.select(where_clause):
    yield PhysCfgBlock.from_json(db,dev,row)
