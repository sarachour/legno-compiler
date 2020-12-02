from enum import Enum
from lab_bench.lib import cstructs,enums

class SignType(str,Enum):
    POS = 'pos'
    NEG = 'neg'

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

    @staticmethod
    def from_abbrev(msg):
        if msg == "+":
            return SignType.POS
        elif msg == "-":
            return SignType.NEG
        else:
            raise Exception("unknown")


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


class RangeType(str,Enum):
    MED = 'medium'
    HIGH = 'high'
    LOW = 'low'
    UNKNOWN = "unknown"

    @staticmethod
    def option_names():
        for opt in RangeType.options():
            yield opt.name

    @staticmethod
    def options():
        yield RangeType.HIGH
        yield RangeType.MED
        yield RangeType.LOW

    @staticmethod
    def from_abbrev(msg):
        if msg == 'm':
            return RangeType.MED
        elif msg == 'l':
            return RangeType.LOW
        elif msg == 'h':
            return RangeType.HIGH
        else:
            raise Exception("unknown range <%s>" % msg)

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

    def abbrev(self):
        if self == RangeType.MED:
            return "m"
        elif self == RangeType.LOW:
            return "l"
        elif self == RangeType.HIGH:
            return "h"
        elif self == RangeType.UNKNOWN:
            return "?"
        else:
            raise Exception("unknown")

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

    def __repr__(self):
        return self.name

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

