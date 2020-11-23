from lab_bench.devices.arduino_due import ArduinoDue
import lab_bench.grendel_util as grendel_util
import lab_bench.generic_util as generic_util

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

  def execute_with_payload(self,header_data,payload_data):
    pad_size= 80
    n_pad = generic_util.compute_pad_bytes(len(header_data), \
                                           pad_size)
    pad_data = bytearray([0]*n_pad)
    rawbuf = header_data+pad_data+payload_data
    self.execute(rawbuf)

  def dispatch(self):
    raise Exception("OverrideMe: fill in with execution and result processing")
