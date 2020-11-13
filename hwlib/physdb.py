import sqlite3
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llenums as llenums
import ops.generic_op as genoplib
import ops.op as oplib

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
model_error real,
label text,
primary key (block,loc,output,static_config,hidden_config)
);
'''
CREATE_PHYS_TABLE = '''
CREATE TABLE IF NOT EXISTS phys_models (
block text,
static_config text,
config text,
params text,
optimize_expr text,
label text,
num_samples integer,
primary key (block,static_config)
);
'''

class PhysicalDatabase:
  class DB(Enum):
    DELTA_MODELS = "delta_models"
    PHYS_MODELS = "phys_models"

  def __init__(self,filename):
    self.filename = filename

    self.conn = sqlite3.connect(self.filename)
    self.curs = self.conn.cursor()
    self.curs.execute(CREATE_PHYS_TABLE)
    self.curs.execute(CREATE_DELTA_TABLE)
    self.conn.commit()
    self.phys_keys = ['block','static_config','config','params','optimize_expr', \
                       'label','num_samples']
    self.delta_keys = ['block','loc','output','static_config','hidden_config', \
                       'config','dataset','delta_model','model_error','label']

  def insert(self,db,_fields):
    assert(isinstance(db,PhysicalDatabase.DB))
    if db == PhysicalDatabase.DB.DELTA_MODELS:
      INSERT = '''INSERT INTO {db} (block,loc,output,static_config,hidden_config,config,dataset,delta_model,model_error,label)
      VALUES ('{block}','{loc}','{output}','{static_config}','{hidden_config}','{config}','{dataset}','{delta_model}',{model_error},'{label}');'''
    elif db == PhysicalDatabase.DB.PHYS_MODELS:
      INSERT = '''INSERT INTO {db} (block,static_config,config,params,optimize_expr,label,num_samples)
      VALUES ('{block}','{static_config}','{config}','{params}','{optimize_expr}','{label}',{num_samples});'''

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
      UPDATE = "UPDATE {db} SET dataset='{dataset}',delta_model='{delta_model}',model_error={model_error},label='{label}' "
    else:
      UPDATE = "UPDATE {db} SET params='{params}',optimize_expr='{optimize_expr}',label='{label}',num_samples={num_samples} "

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


