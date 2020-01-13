import lab_bench.lib.enums as enums
from lab_bench.lib.base_command import Command,ArduinoCommand
import math
import time
import json
import numpy as np
from lab_bench.lib.expcmd.common import *


class MicroGetStatusCmd(ArduinoCommand):

    def __init__(self):
        ArduinoCommand.__init__(self)

    @staticmethod
    def name():
        return 'micro_get_status'

    @staticmethod
    def desc():
        return "[microcontroller] get chip integrator and adc status."


    @staticmethod
    def parse(args):
        return strict_do_parse("",args,MicroGetStatusCmd)

    def __repr__(self):
        return self.name()

    def execute(self,state):
        print("==== overflow summary ====")
        for handle,oflow in state.statuses():
            print("%s status=%s" % (handle,oflow))
        print("=========")

