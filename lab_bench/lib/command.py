import parse as parselib
import lab_bench.lib.cstructs as cstructs
import lab_bench.lib.enums as enums
from lab_bench.lib.chipcmd.use import *
from lab_bench.lib.chipcmd.conn import *
from lab_bench.lib.chipcmd.calib import *
from lab_bench.lib.chipcmd.profile import *
from lab_bench.lib.chipcmd.misc import *
from lab_bench.lib.expcmd.micro_action import *
from lab_bench.lib.expcmd.micro_getter import *
from lab_bench.lib.expcmd.osc import *
from lab_bench.lib.expcmd.client import *
import util.util as util

'''
###################
CIRCUIT COMMANDS
###################
'''

COMMANDS = [
    # dac/adc commands
    UseDACCmd,
    UseADCCmd,
    UseLUTCmd,
    WriteLUTCmd,
    UseIntegCmd,
    UseMultCmd,
    GetIntegStatusCmd,
    GetADCStatusCmd,
    UseFanoutCmd,
    MakeConnCmd,
    # circuit commands that are automatically generated
    DisableCmd,
    BreakConnCmd,
    CalibrateCmd,
    # offset commands
    GetStateCmd,
    ProfileCmd,
    # experiment commands dispatched to microcontroller
    MicroResetCmd,
    MicroRunCmd,
    MicroGetStatusCmd,
    MicroUseOscCmd,
    MicroUseAnalogChipCmd,
    MicroSetSimTimeCmd,
    # oscilloscope-only commands
    OscGetValuesCmd,
    OscSetVoltageRangeCmd,
    OscSetupTrigger,
    OscSetSimTimeCmd,
    # virtual commands, deprecated
    WaitForKeypress
]


def parse(line):
    if line.startswith("#"):
        return None

    args = line.strip().split()
    if len(args) == 0:
        return None
    for cmd in COMMANDS:
        if args[0] == cmd.name():
            obj = cmd.parse(args)
            return obj

    if args[0] == 'help':
        for cmd in COMMANDS:
            print("%s: %s" % (cmd.name(),cmd.desc()))

    return None


def profile(state,obj, \
            clear=False):
    if isinstance(obj,UseCommand):
        dbkey = obj.to_key(calib_obj=state.calib_obj)
        result = state.state_db.get(dbkey)
        print(">> set state")
        obj.execute(state)
        print(">> profile")
        ProfileCmd(obj.block_type,
                   obj.loc.chip,
                   obj.loc.tile,
                   obj.loc.slice,
                   index=obj.loc.index,
                   clear=clear) \
                   .execute(state)



def calibrate(state,obj,recompute=False, \
              calib_obj=util.CalibrateObjective.MIN_ERROR):
    if isinstance(obj,UseCommand):
        dbkey = obj.to_key(calib_obj)
        if not (state.state_db.has(dbkey)) or \
           recompute:
            print(">> resetting defaults")
            DefaultsCommand().execute(state)
            print(">> set state")
            obj.calibrated = False
            obj.execute(state)
            print(">> calibrate %s" % calib_obj.value)
            CalibrateCmd(obj.block_type,
                         obj.loc.chip,
                         obj.loc.tile,
                         obj.loc.slice,
                         obj.loc.index) \
                         .execute(state)


        result = state.state_db.get(dbkey)
