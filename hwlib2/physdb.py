import sqlite3
import hwlib2.device as devlib
import hwlib2.block as blocklib
import hwlib2.adp as adplib
import hwlib2.hcdc.llenums as llenums
import ops.generic_op as ops
import base64
import json
CREATE_TABLE = '''
CREATE TABLE IF NOT EXISTS physical (
block text,
loc text,
output text,
static_config text,
config text,
dataset text,
model text,
primary key (block,loc,static_config)
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
    self.conn.commit()

  def insert(self,fields):
    INSERT = '''INSERT INTO physical (block,loc,static_config,config,dataset,model)
                VALUES ('{block}','{loc}','{static_config}','{config}','{dataset}','{model}');'''
    cmd = INSERT.format(**fields)
    self.curs.execute(cmd)
    self.conn.commit()

  def _where_clause(self,where_clause):
    reqs = []
    for k,v in where_clause.items():
      reqs.append("%s='%s'" % (k,v.replace("'","\\'")))

    if len(reqs) > 0:
      return "WHERE "+(" AND ".join(reqs))
    else:
      return ""

  def update(self,where_clause,fields):
    where_clause_frag = self._where_clause(where_clause)
    assert(len(where_clause_frag) > 0)
    UPDATE = "UPDATE physical SET dataset='{dataset}', model='{model}' "
    cmd = UPDATE.format(**fields) + where_clause_frag
    self.curs.execute(cmd)
    self.conn.commit()

  def select(self,where_clause):
    where_clause_frag = self._where_clause(where_clause)

    keys = ['block','loc','output','static_config','config','dataset','model']
    SELECT = "SELECT * from physical %s" % where_clause_frag
    result = self.curs.execute(SELECT)
    for row in self.curs.fetchall():
      yield dict(zip(keys,row))

class PhysDataset:

  def __init__(self,physblk):
    assert(isinstance(physblk, PhysCfgBlock))
    self.phys = physblk

    # inputs
    self._port_map = {}
    self.relation = {}
    self.data = {}
    self.output = []
    self.meas_mean = []
    self.meas_stdev = []
    self.method = []

    self.output_port = self.phys.block.outputs[self.phys.output.name]
    self.relation[llenums.ProfileOpType.INPUT_OUTPUT]  \
      = self.output_port.relation[self.phys.cfg.mode]

    variables = self.relation[llenums.ProfileOpType.INPUT_OUTPUT].vars()
    self.inputs = {}
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

  def add(self,method,inputs,dynamic_codes,mean,std):
    var_assigns = {}
    for in_port,in_val in inputs.items():
      var_assigns[in_port] = in_val

    for data_port,data_val in dynamic_codes.items():
      var_assigns[data_port] = data_val

    value = self.relation[method].compute(var_assigns)
    self.output.append(value)
    self.meas_mean.append(mean)
    self.meas_stdev.append(std)
    self.method.append(method.value)
    for input_name in self.inputs.keys():
      self.inputs[input_name].append(inputs[input_name])
    for data_name in self.data.keys():
      self.data[data_name].append(dynamic_codes[data_name])

  @staticmethod
  def from_json(physblk,data):
    ds = PhysDataset(physblk)
    for input_name in ds.inputs.keys():
      ds.inputs[input_name] = data['inputs'][input_name]

    ds.output = data['output']
    ds.meas_mean = data['meas']['mean']
    ds.meas_stdev = data['meas']['stdev']
    ds.method = data['meas']['method']
    for data_name,values in ds.data.items():
      for value in values:
        ds.data[data_name] \
          .append(ConfigStmt.from_json(value))
    return ds

  def to_json(self):
    return {
      'inputs': self.inputs,
      'data': self.data,
      'output': self.output,
      'meas': {
        'mean': self.meas_mean,
        'stdev': self.meas_stdev,
        'method': self.method
      }
    }

class PhysDeltaModel:

  def __init__(self,physblk):
    self.phys = physblk

  def to_json(self):
    return None

class PhysCfgBlock:

  def __init__(self,db,blk,loc,out_port,blkcfg):
    assert(isinstance(blkcfg,adplib.BlockConfig))
    assert(isinstance(blk,blocklib.Block))
    assert(isinstance(loc,devlib.Location))
    assert(blkcfg.complete())
    self.block = blk
    self.loc = loc
    self.output = out_port
    self.cfg = blkcfg
    self.db = db
    self.model = PhysDeltaModel(self)
    self.dataset = PhysDataset(self)
    self.load()

  # combinatorial block config (modes) and calibration codes
  @staticmethod
  def get_static_cfg(cfg):
    mode = cfg.mode
    kvs = {}
    kvs['mode'] = mode
    for stmt in cfg.stmts:
      if stmt.t == adplib.ConfigStmtType.STATE:
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
  def static_cfg(self):
    return PhysCfgBlock.get_static_cfg(self.cfg)

  # dynamic values (data)
  def dynamic_cfg(self):
    pass

  def update(self):
    fields = {
      'block': self.block.name,
      'loc': str(self.loc),
      'static_config': self.static_cfg,
      'config': encode_dict(self.cfg.to_json()),
      'dataset':encode_dict(self.dataset.to_json()),
      'model': encode_dict(self.model.to_json())
    }
    where_clause = {
      'block': self.block.name,
      'loc': str(self.loc),
      'static_config': self.static_cfg,
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
      'static_config': self.static_cfg,
    }
    matches = list(self.db.select(where_clause))
    if len(matches) == 1:
      json_dataset = decode_dict(matches[0]['dataset'])
      self.dataset = PhysDataset.from_json(self,json_dataset)

  def add_datapoint(self,cfg,inputs,method,mean,std):
    assert(self.static_cfg == PhysCfgBlock.get_static_cfg(cfg))
    self.dataset.add(method,inputs,PhysCfgBlock.get_dynamic_cfg(cfg),mean,std)
    self.update()
