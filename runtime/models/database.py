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
from enum import Enum


CREATE_DATA_TABLE = '''
CREATE TABLE IF NOT EXISTS profile_data (
block text,
loc text,
output text,
static_config text,
hidden_config text,
method text,
dataset text,
primary key (block,loc,output,static_config,hidden_config,method)
);
'''

CREATE_DELTA_TABLE = '''
CREATE TABLE IF NOT EXISTS delta_models (
block text,
loc text,
output text,
static_config text,
hidden_config text,
model text,
calib_obj text,
model_error text,
primary key (block,loc,output,static_config,hidden_config,calib_obj)
);
'''

CREATE_PHYS_TABLE = '''
CREATE TABLE IF NOT EXISTS phys_models (
block text,
static_config text,
model text,
primary key (block,static_config)
);
'''

class PhysicalDatabase:
  class DB(Enum):
    DELTA_MODELS = "delta_models"
    PHYS_MODELS = "phys_models"
    PROFILE_DATASET = "profile_data"

  def __init__(self,filename):
    self.filename = filename

    self.conn = sqlite3.connect(self.filename)
    self.curs = self.conn.cursor()
    self.curs.execute(CREATE_PHYS_TABLE)
    self.curs.execute(CREATE_DELTA_TABLE)
    self.curs.execute(CREATE_DATA_TABLE)
    self.conn.commit()
    self.keys = {}
    self.keys[PhysicalDatabase.DB.PHYS_MODELS] = ['block','static_config','model']
    self.keys[PhysicalDatabase.DB.DELTA_MODELS] = ['block','loc','output', \
                                                   'static_config','hidden_config', \
                                                   'model','calib_obj','model_error']
    self.keys[PhysicalDatabase.DB.PROFILE_DATASET] = ['block','loc','output', \
                                              'static_config','hidden_config', \
                                              'method','dataset']

    self.updateable = {}
    self.updateable[PhysicalDatabase.DB.PHYS_MODELS] = ['model']
    self.updateable[PhysicalDatabase.DB.DELTA_MODELS] = ['model','model_error']
    self.updateable[PhysicalDatabase.DB.PROFILE_DATASET] = ['dataset']


  def insert(self,db,fields):
    assert(isinstance(db,PhysicalDatabase.DB))
    row_fields = ",".join(self.keys[db])
    row_values = ",".join(map(lambda k: "'{%s}'" % k, self.keys[db]))
    INSERT = '''INSERT INTO %s (%s) VALUES (%s)''' % (db.value, \
                                                        row_fields, \
                                                        row_values)
    cmd = INSERT.format(**fields)
    self.curs.execute(cmd)
    self.conn.commit()

  def _where_clause(self,db,fields):
    assert(isinstance(db,PhysicalDatabase.DB))
    reqs = []
    where_clause = dict(filter(lambda tup: tup[0] in self.keys[db], \
                               fields.items()))
    for k,v in where_clause.items():
      reqs.append("%s='%s'" % (k,v.replace("'","''")))

    if len(reqs) > 0:
      return "WHERE "+(" AND ".join(reqs))
    else:
      return ""

  def update(self,db,where_clause,fields):
    assert(isinstance(db,PhysicalDatabase.DB))
    where_clause_frag = self._where_clause(db,where_clause)
    assert(len(where_clause_frag) > 0)
    upd_frag = ",".join(map(lambda upd: "%s='{%s}'" % (upd,upd), \
                            self.updateable[db]))

    UPDATE = "UPDATE %s SET %s %s" % (db.value,upd_frag, \
                                      where_clause_frag)
    cmd = UPDATE.format(**fields)
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
    for row in self._select(db,"*",fields):
      yield dict(zip(self.keys[db],row))

  def select_field(self,db,field_names,where_clause):
    assert(isinstance(db,PhysicalDatabase.DB))
    for field_name in field_names:
      if not (field_name in self.keys[db]):
        raise Exception("field <%s> not in database <%s>" % (field_name,db.value))

    select_clause = ",".join(field_names)
    for field_values in self._select(db, \
                                     select_clause, \
                                     where_clause,\
                                     distinct=True):
      yield dict(zip(field_names,field_values))


