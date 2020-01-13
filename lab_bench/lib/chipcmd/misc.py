import lab_bench.lib.enums as enums
from enum import Enum
from lab_bench.lib.chipcmd.use import UseCommand
from lab_bench.lib.chipcmd.data import *
from lab_bench.lib.chipcmd.common import *
from lab_bench.lib.base_command import AnalogChipCommand
import lab_bench.lib.util as util
import construct



class DefaultsCommand(ArduinoCommand):

    def __init__(self):
        ArduinoCommand.__init__(self)

    @staticmethod
    def name():
        return 'micro_defaults'

    @staticmethod
    def desc():
        return "[microcontroller] set configs to default values."

    def build_ctype(self):
        return build_circ_ctype({
            'type':enums.CircCmdType.DEFAULTS.name,
            'data':{
                'circ_loc':CircLoc(0,0,0).build_ctype()
            }
        })


    @staticmethod
    def parse(args):
        return strict_do_parse("", args, DefaultsCommand)

    def __repr__(self):
        return self.name()


class WriteLUTCmd(ArduinoCommand):

    def __init__(self,chip,tile,slice,variables,expr):
        ArduinoCommand.__init__(self)
        self._loc = CircLoc(chip,tile,slice)
        self._block = enums.BlockType.LUT


        if not self._loc.index is None:
            self.fail("lut has no index <%d>" % loc.index)

        self._expr = expr
        self._variables = variables
        if not (len(self._variables) == 1):
            raise Exception('unexpected number of variables: %s' % variables)


    @property
    def loc(self):
        return self._loc

    @property
    def expr(self):
        return self._expr

    @staticmethod
    def desc():
        return "write data to lut block on the hdacv2 board"


    @staticmethod
    def parse(args):
        return WriteLUTCmd._parse(args,WriteLUTCmd)

    @staticmethod
    def _parse(args,cls):
        result = parse_pattern_use_block(args,0,0,0,
                                         cls.name(),
                                         source=None,
                                         expr=True)
        if result.success:
            data = result.value
            return cls(
                data['chip'],
                data['tile'],
                data['slice'],
                data['vars'],
                data['expr']
            )
        else:
            raise Exception(result.message)

    def build_dtype(self,buf):
        return construct.Array(len(buf),
                        construct.Float32l)


    def build_ctype(self,offset=None,n=None):
        # inverting flips the sign for some wacky reason, given the byte
        # representation is signed
        return build_circ_ctype({
            'type':enums.CircCmdType.WRITE_LUT.name,
            'data':{
                'write_lut':{
                    'loc':self._loc.build_ctype(),
                    'offset':offset,
                    'n':n
                }
            }
        })

    @staticmethod
    def name():
        return 'write_lut'

    def __repr__(self):
        vstr = ",".join(self._variables)
        st = "%s %s %s %s [%s] %s" % \
              (self.name(),
               self.loc.chip,self.loc.tile, \
               self.loc.slice,
               vstr,self._expr)
        return st



    def execute_command(self,state):
        if state.dummy:
            return

        # ADCs are centered at 128, from [20,235]

        values = [0.0]*256
        # FIXME: hack. get the values from the cached dac
        for idx in range(0,256):
            v = (idx-128.0)/128.0
            assigns = dict(zip(self._variables,[v]))
            value = util.eval_func(self.expr,assigns)
            clamp_value = min(max(value,-1.0),1.0)
            values[idx] = float(clamp_value)

        for idx,val in enumerate(values):
            print("%s = %f" % (idx,val))

        resp = ArduinoCommand.execute_command(self,state,
                                              raw_data=list(values),
                                              n_data_bytes=256,
                                              elem_size=4)
        return resp


class GetADCStatusCmd(AnalogChipCommand):
    def __init__(self,chip,tile,slice):
        AnalogChipCommand.__init__(self)
        self._loc = CircLoc(chip,tile,slice)

    @property
    def loc(self):
        return self._loc

    @staticmethod
    def name():
        return 'get_adc_status'

    @staticmethod
    def parse(args):
        result = parse_pattern_use_block(args,0,0,0,
                                         GetADCStatusCmd.name(),
                                         debug=False)
        if result.success:
            data = result.value
            return GetADCStatusCmd(
                data['chip'],
                data['tile'],
                data['slice']
            )
        else:
            raise Exception(result.message)


    def analyze(self):
        return self

    def build_ctype(self):
        # inverting flips the sign for some wacky reason, given the byte
        # representation is signed
        return build_circ_ctype({
            'type':enums.CircCmdType.GET_ADC_STATUS.name,
            'data':{
                'circ_loc':self._loc.build_ctype()
            }
        })

    def execute_command(self,state):
        if state.dummy:
            return

        resp = AnalogChipCommand.execute_command(self,state)
        handle = "adc.%s" % self.loc
        code = resp.data(0)
        print("status_val: %s" % code)
        state.set_status(handle, code)



    def __repr__(self):
        st = "get_adc_status %s %s %s" % \
              (self.loc.chip,self.loc.tile, \
               self.loc.slice)
        return st


class GetIntegStatusCmd(AnalogChipCommand):
    def __init__(self,chip,tile,slice):
        AnalogChipCommand.__init__(self)
        self._loc = CircLoc(chip,tile,slice)

    @property
    def loc(self):
        return self._loc

    @staticmethod
    def name():
        return 'get_integ_status'

    @staticmethod
    def parse(args):
        result = parse_pattern_use_block(args,0,0,0,
                                         GetIntegStatusCmd.name(),
                                         debug=False)
        if result.success:
            data = result.value
            return GetIntegStatusCmd(
                data['chip'],
                data['tile'],
                data['slice']
            )
        else:
            raise Exception(result.message)


    def analyze(self):
        return self

    def build_ctype(self):
        # inverting flips the sign for some wacky reason, given the byte
        # representation is signed
        return build_circ_ctype({
            'type':enums.CircCmdType.GET_INTEG_STATUS.name,
            'data':{
                'circ_loc':self._loc.build_ctype()
            }
        })

    def execute_command(self,state):
        if state.dummy:
            return

        resp = AnalogChipCommand.execute_command(self,state)
        handle = "integ.%s" % self.loc
        oflow = True if resp.data(0) == 1 else False
        print("status_val: %s" % oflow)
        state.set_status(handle, oflow)



    def __repr__(self):
        st = "get_integ_status %s %s %s" % \
              (self.loc.chip,self.loc.tile, \
               self.loc.slice)
        return st

