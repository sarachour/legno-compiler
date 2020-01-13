from lab_bench.devices.arduino_due import ArduinoDue
from lab_bench.devices.sigilent_osc import Sigilent1020XEOscilloscope
import lab_bench.devices.sigilent_osc as osclib

from lab_bench.lib.base_command import FlushCommand, ArduinoCommand
from lab_bench.lib.base_command import AnalogChipCommand
import lab_bench.lib.util as util
import lab_bench.lib.chipcmd.state as state
import time
import numpy as np
import math

class GrendelEnv:

    def __init__(self,osc_ip,osc_port,ard_native,calib_obj,\
                 validate=False):
        if not validate:
            self.arduino = ArduinoDue(native=ard_native)
            self.oscilloscope = Sigilent1020XEOscilloscope(
                osc_ip, osc_port)
        else:
            self.arduino = None
            self.oscilloscope = None


        ## State committed to chip
        self.use_osc = False;
        self.calib_obj = calib_obj

        self.state_db = state.BlockStateDatabase()
        self.use_analog_chip = None;
        self._status = {}

        self.reset();
        self.sim_time = None
        self.input_time = None
        self.dummy = validate

    def set_status(self,handle,oflow):
        self._status[handle] = oflow

    def statuses(self):
        for handle,oflow in self._status.items():
            yield handle,oflow


    def reset(self):
        self.use_analog_chip = False;
        self.inputs = {}


    def close(self):
        if not self.arduino is None:
            self.arduino.close()
        if not self.oscilloscope is None:
            self.oscilloscope.close()

    def initialize(self):
        if self.dummy:
            return

        #try:
        print("[[ setup oscilloscope ]]")
        self.oscilloscope.setup()
        if not self.oscilloscope.ready():
            print("[[no oscilloscope]]")
            self.oscilloscope = None

        self.arduino.open()
        if not self.arduino.ready():
            print("[[no arduino]]")
            self.arduino = None

        if not self.arduino is None:
            flush_cmd = FlushCommand()
            while not flush_cmd.execute(self):
                continue

