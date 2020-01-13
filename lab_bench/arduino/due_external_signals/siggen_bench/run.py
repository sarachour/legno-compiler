import serial
import time
import re
from tqdm import tqdm
import numpy as np

def get_arduino_path():
  import os
  for root, dirs, files in os.walk("/dev/", topdown=False):
    for name in files:
      if "tty.usbmodem" in name:
        return "/dev/%s" % name

      elif "ttyACM" in name:
        return "/dev/%s" % name

  return None


class ArduinoDue:

    def __init__(self,native=True):
        self._baud_rate = 115200
        self._serial_port = get_arduino_path()
        self._comm = None

    def close(self):
        if not self._comm is None:
            self._comm.close()

    def ready(self):
        return not self._comm is None

    def open(self):
        print("%s:%s" % (self._serial_port,self._baud_rate))
        try:
            self._comm= serial.Serial(self._serial_port, self._baud_rate)
        except serial.SerialException as e:
            print("[ArduinoDue][setup][ERROR] %s" % e)
            self._comm = None
            return

        startup_time = 0.2
        n_divs = 100
        delta = startup_time/n_divs
        for _ in tqdm(np.linspace(0,startup_time,n_divs)):
            time.sleep(delta)

        print("waiting for input");
        line = self.try_readline()
        while not line is None:
            print(line)
            line = self.try_readline()

        self.flush()
        return True

    def readline(self):
        line_bytes = self._comm.readline()
        line_valid_bytes = bytearray(filter(lambda b: b<128, line_bytes))
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

    def writeline(self,string):
        msg = "%s\r\n" % string
        self.write(msg)

    def write_newline(self):
        self.write("\r\n")

    def flush(self):
        self._comm.flushInput()
        self._comm.flushOutput()

    def write_bytes(self,byts):
        isinstance(byts,bytearray)
        nbytes = 0;
        BATCH = 1
        byte_gen = tqdm(range(0,len(byts)))
        for i in byte_gen:
            byte_gen.set_description("writing byte %d" % i)
            nbytes += self._comm.write(byts[i:i+1])
            self._comm.flush()
            time.sleep(0.01)

        self._comm.flush()

    def write(self,msg):
        self.write_bytes(msg.encode())


sig2code = {
  "zero": 'z',
  "sin": 's',
  "kal-bias": 'k',
  "anom-ampl": 'a',
  "anom-freq": 'f',
  "anom-bias": 'b',
  "heart-reg": 'h',
  "heart-irreg": 'i'
}
due = ArduinoDue()
print("==== opening ====");
due.open()
for key in sig2code.keys():
  print("  %s" % key)

sig = None
while not sig in sig2code:
  sig = input("choose signal: ")

due.write(sig2code[sig])

while(True):
    line = due.try_readline()
    while not line is None:
      print(line)
      line = due.try_readline()

print("done");
