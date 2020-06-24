from lab_bench.devices.arduino_due import ArduinoDue
import lab_bench.grendel_util as grendel_util

class GrendelRunner:


  def __init__(self, \
               board_name="board6", \
               file_desc=None, \
               native=False):
    self.due = ArduinoDue(file_desc,native=native)
    self.board_name = board_name

  def initialize(self):
    self.due.open()

  def close(self):
    self.due.close()

  def result(self):
    return grendel_util.get_response(self.due)

  def execute(self,cmd):
    self.due.write_bytes(cmd)
    self.due.write_newline()

  def send_data(self,data,chunksize=4):
    pass

  def dispatch(self):
    raise Exception("OverrideMe: fill in with execution and result processing")
