from enum import Enum

class CmdType(Enum):
    NULL_CMD = "no_cmd"
    CIRC_CMD = "circ_cmd"
    EXPERIMENT_CMD = "exper_cmd"
    FLUSH_CMD = "flush_cmd"

class CircCmdType(Enum):
    DISABLE = 'disable';
    CONNECT = 'connect';
    BREAK = 'break';
    CALIBRATE = 'calibrate';
    GET_STATUS = 'get_status';
    WRITE_LUT = "write_lut";
    SET_STATE = "set_state";
    GET_STATE = "get_state";
    DEFAULTS = "defaults";
    PROFILE = "profile";
    NULLCMD = "no_circ_cmd"

class ExpCmdType(Enum):
    RESET = 'reset';
    USE_ANALOG_CHIP = 'use_analog_chip';
    SET_SIM_TIME= 'set_sim_time';
    USE_OSC = 'use_osc';
    RUN = 'run';


class BlockType(str,Enum):
    DAC = 'dac';
    ADC = 'adc';
    CHIP_INPUT = 'chip_input';
    CHIP_OUTPUT = 'chip_output';
    TILE_INPUT = "tile_input";
    TILE_OUTPUT = "tile_output";
    MULT = "mult";
    INTEG = "integ";
    FANOUT = "fanout";
    LUT = "lut";
    NONE = "<none>";

    def code(self):
        mapping = {
            BlockType.DAC: 0,
            BlockType.MULT: 5,
            BlockType.INTEG: 6,
            BlockType.FANOUT: 7,
            BlockType.LUT: 8,
            BlockType.ADC: 9
        }
        return mapping[self]

class BoolType(str,Enum):
    TRUE = 'true'
    FALSE = 'false'

    def boolean(self):
        if self == BoolType.TRUE:
            return True
        else:
            return False

    @staticmethod
    def from_bool(b):
        if b:
            return BoolType.TRUE
        else:
            return BoolType.FALSE

    @staticmethod
    def from_code(code):
        if code == 0:
            return BoolType.FALSE
        else:
            return BoolType.TRUE

    def code(self):
        if BoolType.TRUE == self:
            return 1
        else:
            return 0


class RangeType(str,Enum):
    MED = "m"
    HIGH = 'h'
    LOW = "l"
    UNKNOWN = "x"

    @staticmethod
    def option_names():
        for opt in RangeType.options():
            yield opt.name

    @staticmethod
    def options():
        yield RangeType.HIGH
        yield RangeType.MED
        yield RangeType.LOW
        yield RangeType.UNKNOWN

    def coeff(self):
        if self == RangeType.MED:
            return 1.0
        elif self == RangeType.LOW:
            return 0.1
        elif self == RangeType.HIGH:
            return 10.0
        else:
            raise Exception("unknown")

    @staticmethod
    def has(v):
      assert(isinstance(v,Enum))
      for name in RangeType.option_names():
        if v.name == name:
          return True
      return False

    def code(self):
        if self == RangeType.MED:
            return 1
        elif self == RangeType.LOW:
            return 2
        elif self == RangeType.HIGH:
            return 0
        elif self == RangeType.UNKNOWN:
            return 3
        else:
            raise Exception("unknown")


class LUTSourceType(str,Enum):
    EXTERN = 'extern'
    ADC0 = "adc0"
    ADC1 = "adc1"
    CONTROLLER = "controller"


    def code(self):
        if self == LUTSourceType.EXTERN:
            return 2
        elif self == LUTSourceType.ADC0:
            return 0
        elif self == LUTSourceType.ADC1:
            return 1
        else:
            raise Exception("unknown: %s" % self)


    def abbrev(self):
        if self == LUTSourceType.EXTERN:
            return "ext"
        elif self == LUTSourceType.ADC0:
            return "adc0"
        elif self == LUTSourceType.ADC1:
            return "adc1"
        else:
            raise Exception("not handled: %s" % self)


    @staticmethod
    def from_abbrev(msg):
        if msg == 'ext':
            return LUTSourceType.EXTERN
        elif msg == 'adc0':
            return LUTSourceType.ADC0
        elif msg == 'adc1':
            return LUTSourceType.ADC1
        else:
            raise Exception("not handled: %s" % self)


class DACSourceType(str,Enum):
    # default
    MEM = 'memory'
    EXTERN = 'external'
    LUT0 = "lut0"
    LUT1 = "lut1"



    def code(self):
        if self == DACSourceType.MEM:
            return 0
        elif self == DACSourceType.EXTERN:
            return 1
        elif self == DACSourceType.LUT0:
            return 2
        elif self == DACSourceType.LUT1:
            return 3
        else:
            raise Exception("unknown: %s" % self)

    @staticmethod
    def from_abbrev(msg):
        if msg == 'mem':
            return DACSourceType.MEM
        elif msg == 'ext':
            return DACSourceType.EXTERN
        elif msg == 'lut0':
            return DACSourceType.LUT0
        elif msg == 'lut1':
            return DACSourceType.LUT1
        else:
            raise Exception("not handled: %s" % self)

    def abbrev(self):
        if self == DACSourceType.MEM:
            return "mem"
        elif self == DACSourceType.EXTERN:
            return "ext"
        elif self == DACSourceType.LUT0:
            return "lut0"
        elif self == DACSourceType.LUT1:
            return "lut1"
        else:
            raise Exception("not handled: %s" % self)

class PortType(str,Enum):
    IN0 = "in0"
    IN1 = "in1"
    OUT0 = "out0"
    OUT1 = "out1"
    OUT2 = "out2"

    @staticmethod
    def default():
        return PortType.IN0

    def to_code(self):
        codes = {
            PortType.IN0: 0,
            PortType.IN1: 1,
            PortType.OUT0: 2,
            PortType.OUT1: 3,
            PortType.OUT2: 4
        }
        return codes[self]

    @staticmethod
    def from_code(i):
        codes = {
            0: PortType.IN0,
            1: PortType.IN1,
            2: PortType.OUT0,
            3: PortType.OUT1,
            4: PortType.OUT2
        }
        return codes[i]

class SignType(str,Enum):
    POS = '+'
    NEG = '-'

    @staticmethod
    def option_names():
        for opt in SignType.options():
            yield opt.name


    @staticmethod
    def has(v):
      assert(isinstance(v,Enum))
      for name in SignType.option_names():
        if v.name == name:
          return True
      return False


    @staticmethod
    def options():
        yield SignType.POS
        yield SignType.NEG


    def coeff(self):
        if SignType.POS == self:
            return 1.0
        elif SignType.NEG == self:
            return -1.0
        else:
            raise Exception("unknown")

    def abbrev(self):
        if self == SignType.POS:
            return '+'
        elif self == SignType.NEG:
            return '-'
        else:
            raise Exception("unknown")

    def code(self):
        if self == SignType.POS:
            return False
        elif self == SignType.NEG:
            return True

    def __repr__(self):
        return self.abbrev()


class LUTSourceType(str,Enum):
    EXTERN = 'ext'
    ADC0 = "adc0"
    ADC1 = "adc1"
    CONTROLLER = "ctrl"


    def code(self):
        if self == LUTSourceType.EXTERN:
            return 2
        elif self == LUTSourceType.ADC0:
            return 0
        elif self == LUTSourceType.ADC1:
            return 1
        else:
            raise Exception("unknown: %s" % self)


class DACSourceType(str,Enum):
    # default
    MEM = 'mem'
    EXTERN = 'ext'
    LUT0 = "lut0"
    LUT1 = "lut1"



    def code(self):
        if self == DACSourceType.MEM:
            return 0
        elif self == DACSourceType.EXTERN:
            return 1
        elif self == DACSourceType.LUT0:
            return 2
        elif self == DACSourceType.LUT1:
            return 3
        else:
            raise Exception("unknown: %s" % self)
