import lab_bench.lib.enums as enums
import lab_bench.lib.util as util
from lab_bench.lib.base_command import Command,ArduinoCommand
from lab_bench.lib.expcmd.common import *
import lab_bench.lib.util as util
import math
import time
import json
import numpy as np
import construct

class MicroResetCmd(ArduinoCommand):

    def __init__(self):
        ArduinoCommand.__init__(self)

    @staticmethod
    def name():
        return 'micro_reset'

    @staticmethod
    def desc():
        return "[microcontroller] reset any set flags, values and buffers on the microcontroller."

    def build_ctype(self):
        return build_exp_ctype({
            'type':enums.ExpCmdType.RESET.name,
            'args':{
                'ints':[0,0,0],
            },
            'flag':False
        })


    def execute(self,state):
        state.reset()
        ArduinoCommand.execute(self,state)


    @staticmethod
    def parse(args):
        return strict_do_parse("", args, MicroResetCmd)

    def __repr__(self):
        return self.name()


class MicroSetSimTimeCmd(ArduinoCommand):

    def __init__(self,sim_time):
        ArduinoCommand.__init__(self)
        if(sim_time <= 0):
            self.fail("invalid simulation time: %s" % sim_time)

        self._sim_time = sim_time


    def build_ctype(self):
        return build_exp_ctype({
            'type':enums.ExpCmdType.SET_SIM_TIME.name,
            'args':{
                'floats':[self._sim_time,0.0,0.0]
            },
            'flag':False
        })


    @staticmethod
    def name():
        return 'micro_set_sim_time'

    def __repr__(self):
        return "%s %.3e" % (self.name(),self._sim_time)


    @staticmethod
    def parse(args):
        return strict_do_parse("{sim_time:g}", args, \
                               MicroSetSimTimeCmd)


    def execute(self,state):
        state.sim_time = self._sim_time
        ArduinoCommand.execute(self,state)



    @staticmethod
    def desc():
        return "[microcontroller] set the simulation time and input time"


class MicroUseAnalogChipCmd(ArduinoCommand):

    def __init__(self):
        ArduinoCommand.__init__(self)

    @staticmethod
    def name():
        return 'micro_use_chip'

    @staticmethod
    def desc():
        return "mark the analog chip as used."


    def build_ctype(self):
        return build_exp_ctype({
            'type':enums.ExpCmdType.USE_ANALOG_CHIP.name,
            'args':{
                'ints':[0,0,0],
            },
            'flag':False
        })


    def execute(self,state):
        state.use_analog_chip = True
        ArduinoCommand.execute(self,state)

    @staticmethod
    def parse(args):
        return strict_do_parse("",args,MicroUseAnalogChipCmd)

    def __repr__(self):
        return self.name()


class MicroUseOscCmd(ArduinoCommand):

    def __init__(self):
        ArduinoCommand.__init__(self)

    @staticmethod
    def name():
        return 'micro_use_osc'

    @staticmethod
    def desc():
        return "[microcontroller] setup trigger on pin 23 for oscilloscope."



    @staticmethod
    def parse(args):
        return strict_do_parse("",args,MicroUseOscCmd)


    def build_ctype(self):
        return build_exp_ctype({
            'type':enums.ExpCmdType.USE_OSC.name,
            'args':{
                'ints':[0,0,0],
            },
            'flag':False
        })



    def execute(self,state):
        state.use_osc = True
        ArduinoCommand.execute(self,state)

    def __repr__(self):
        return self.name()


class MicroRunCmd(ArduinoCommand):

    def __init__(self):
        ArduinoCommand.__init__(self)

    @staticmethod
    def name():
        return 'micro_run'

    @staticmethod
    def desc():
        return "[microcontroller] run the experiment."


    @staticmethod
    def parse(args):
        return strict_do_parse("",args,MicroRunCmd)


    def build_ctype(self):
        return build_exp_ctype({
            'type':enums.ExpCmdType.RUN.name,
            'args':{
                'ints':[0,0,0],
            },
            'flag':False
        })


    def execute(self,state):
        resp = ArduinoCommand.execute(self,state)

    def __repr__(self):
        return self.name()

