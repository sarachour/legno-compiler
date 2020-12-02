import serial
import time
import re
from tqdm import tqdm
import numpy as np
import os


class ArduinoDue:
  def __init__(self, file_desc, native=True):
    self._baud_rate = 115200
    if file_desc is None:
      file_desc = ArduinoDue.find_device()

    if file_desc is None:
      raise Exception("could not find arduino")

    self._serial_port = file_desc
    self._comm = None

  @staticmethod
  def find_device():
    for root, dirs, files in os.walk("/dev/", topdown=False):
      for name in files:
        if "tty.usbmodem" in name:
          return "/dev/%s" % name
        elif "ttyACM" in name:
          return "/dev/%s" % name

    return None

  def close(self):
    if not self._comm is None:
      self._comm.close()

  def ready(self):
    return not self._comm is None

  def open(self):
    print("%s:%s" % (self._serial_port, self._baud_rate))
    try:
      self._comm = serial.Serial(self._serial_port, self._baud_rate)
    except serial.SerialException as e:
      print("[ArduinoDue][setup][ERROR] %s" % e)
      self._comm = None
      return

    startup_time = 2.0
    n_divs = 100
    delta = startup_time / n_divs
    print("starting up...")
    for _ in tqdm(np.linspace(0, startup_time, n_divs)):
      time.sleep(delta)

    line = self.try_readline()
    while not line is None:
      print(line)
      line = self.try_readline()

    self.flush()
    return True

  def readline(self):
    line_bytes = self._comm.readline()
    line_valid_bytes = bytearray(filter(lambda b: b < 128, line_bytes))
    strline = line_valid_bytes.decode('utf-8')
    return strline

  def reads_available(self):
    return self._comm.in_waiting > 0

  def try_readline(self):
    if self._comm.in_waiting > 0:
      line = self.readline()
    else:
      line = None

    return line

  def writeline(self, string):
    msg = "%s\r\n" % string
    self.write(msg)

  def write_newline(self):
    self.write("\r\n")

  def flush(self):
    self._comm.flushInput()
    self._comm.flushOutput()

  def write_bytes(self, byts):
    isinstance(byts, bytearray)
    nbytes = 0
    BATCH = 1
    nbytes += self._comm.write(byts)
    self._comm.flush()
    #time.sleep(0.01)

  def write(self, msg):
    self.write_bytes(msg.encode())
