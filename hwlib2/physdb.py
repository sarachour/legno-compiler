import sqlite3
import hwlib2.device as devlib

CREATE_TABLE = '''
CREATE TABLE physical (
block text;
loc text;
output text;
parametric_cfg text;
cfg text;
data text;
model text;
primary(inst,cfg);
);
'''

class PhysicalDatabase:

  def __init__(self,board_name):
    self.board = board_name
    self.filename = "%s.db" % self.board
    self.conn = sqlite3.connect(self.filename)
    self.curs = self.conn.cursor()

  def get(self,blk,loc,output,blkcfg):
    row = PhysDataRow(self,blk,loc,output,blkcfg)
    row.load()
    return row

  def filter(self,func):
    pass

class PhysDataRow:

  def __init__(self,db,blk,loc,out_port,blkcfg):
    self.blk = blk
    self.loc = loc
    self.output = out_port
    self.cfg = blkcfg
    self.db = db


  # combinatorial block config (modes) and calibration codes
  @property
  def static_cfg(self):
    pass

  # dynamic values (data)
  def dynamic_cfg(self):
    pass

  def load(self):
    self.model = None
    self.data = None
    pass

  def write(self):
    pass

  def add_datapoint(self,in0,in1,out_port,method,mean,std):
    raise NotImplementedError
