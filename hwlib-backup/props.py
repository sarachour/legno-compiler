import hwlib.units as units
from enum import Enum

class Properties:
    CURRENT = 'current'
    VOLTAGE = 'voltage'
    DIGITAL = 'digital'
    ANALOG = 'analog'

    def __init__(self,typ):
        typ = Properties.ANALOG if Properties.is_analog(typ) else typ

        self._type = typ


    @property
    def type(self):
        return self._type

    def analog(self):
        return Properties.is_analog(self._type)

    @staticmethod
    def is_analog(typ):
        return typ == Properties.CURRENT or typ == Properties.VOLTAGE \
            or typ == Properties.ANALOG

CURRENT = Properties.CURRENT
VOLTAGE = Properties.VOLTAGE
DIGITAL = Properties.DIGITAL
ANALOG = Properties.ANALOG
from ops.interval import Interval, IRange, IValue


class AnalogProperties(Properties):
    class SignalType(Enum):
        CONSTANT = "constant"
        DYNAMIC = "dynamic"

    def __init__(self):
        Properties.__init__(self,Properties.ANALOG)
        self._bounds = (None,None,units.unknown)
        self._bandwidth = (None,None,units.unknown)
        self._physical = False

    def set_physical(self,v):
        self._physical = v

    @property
    def is_physical(self):
        return self._physical

    def set_bandwidth(self,lower,upper,unit):
        assert(lower is None or upper is None or lower <= upper)
        self._bandwidth = (lower,upper,unit)
        return self

    def set_interval(self,lower,upper,unit):
        assert(lower is None or upper is None or lower <= upper)
        self._bounds = (lower,upper,unit)
        return self

    def interval(self):
        lb,ub,unit = self._bounds
        return IRange(lb,ub)

    def bandwidth(self):
         lb,ub,unit = self._bandwidth
         lb = lb*unit if not lb is None else None
         ub = ub*unit if not ub is None else None
         return Interval.type_infer(lb,ub)


    def check(self):
        assert(not self._bounds[0] is None)
        assert(not self._bounds[1] is None)
        assert(not self._bounds[1] is units.unknown)

    def __repr__(self):
        return "Analog(bounds=%s, bw=%s, phys=%s)" \
            % (self._bounds,self._bandwidth, \
               self._physical)

class DigitalProperties(Properties):
    class ClockType(Enum):
        CLOCKED = "clocked"
        CONTINUOUS = "continuous"
        CONSTANT = "constant"
        UNKNOWN = "unknown"

    class SignalType(Enum):
        CONSTANT = "constant"
        DYNAMIC = "dynamic"

    def __init__(self):
        Properties.__init__(self,Properties.DIGITAL)
        self._values = None
        self._max_error = None
        self._kind = DigitalProperties.ClockType.UNKNOWN
        # for clocked
        self._sample_rate = (None,units.unknown)
        # for continuous
        self._bandwidth = (None,None,units.unknown)
        self._resolution = 1.0
        self._coverage = 1.0

    def __repr__(self):
        clk = "Synch(kind=%s, rate=%s, bw=%s)" % \
              (self._kind,self._sample_rate, self._bandwidth)
        dig = "Digital(min=%s, max=%s)" % (min(self._values), max(self._values))
        return dig + " " + clk

    def set_continuous(self,lb,ub,unit=1.0):
        self._kind = DigitalProperties.ClockType.CONTINUOUS
        self._bandwidth = (lb,ub,unit)
        return self

    def set_clocked(self,sample_rate,max_samples,unit=1.0):
        self._kind = DigitalProperties.ClockType.CLOCKED
        self._sample_rate = (sample_rate,unit)
        self._max_samples = max_samples
        return self

    def set_coverage(self,res):
        assert(res >= 0.0)
        assert(res <= 1.0)
        self._coverage = res

    def set_resolution(self,res):
        assert(res >= 1.0)
        self._resolution = res

    def interval(self):
        lb = min(self.values())
        ub = max(self.values())
        return IRange(lb,ub)

    @property
    def coverage(self):
        return self._coverage

    def value(self,value):
        diff = map(lambda x : (x,abs(x-value)),self._values)
        choices = sorted(diff, key=lambda q: q[1])
        closest_value, error = choices[0]
        return closest_value

    @property
    def kind(self):
        return self._kind

    @property
    def resolution(self):
        return self._resolution


    @property
    def sample_rate(self):
        rate,unit = self._sample_rate
        if rate is None:
            return None
        return rate*unit


    @property
    def max_samples(self):
        return self._max_samples

    def bandwidth(self):
         lb,ub,unit = self._bandwidth
         lb = lb*unit if not lb is None else None
         ub = ub*unit if not ub is None else None
         return Interval.type_infer(lb,ub)


    def set_values(self,values):
        self._values = list(values)
        return self

    def index(self,value):
        return self._values.index(value)

    def values(self):
        return self._values

    def set_constant(self):
        self._kind = DigitalProperties.ClockType.CONSTANT
        return self

    @property
    def is_constant(self):
        return self._kind == DigitalProperties.ClockType.CONSTANT

    def check(self):
        assert(not self._values is None)
        assert(not self._max_error is None)
        assert(self._kind != DigitalProperties.ClockType.UNKNOWN)
        return self
