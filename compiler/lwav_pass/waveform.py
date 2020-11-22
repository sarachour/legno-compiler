from enum import Enum

class Waveform:
    class TimeUnits(Enum):
        WALL_CLOCK_SECONDS = "wall_clock_sec"
        DS_TIME_UNITS = "ds_time_units"

        def rec_units(self):
            if self == Waveform.TimeUnits.DS_TIME_UNITS:
                return Waveform.TimeUnits.WALL_CLOCK_SECONDS
            else:
                return Waveform.TimeUnits.DS_TIME_UNITS

    class AmplUnits(Enum):
        VOLTAGE = "voltage"
        DS_QUANTITY = "ds_quantity"

        def rec_units(self):
            if self == Waveform.AmplUnits.VOLTAGE:
                return Waveform.AmplUnits.DS_QUANTITY
            else:
                return Waveform.AmplUnits.VOLTAGE

    def __init__(self, \
                 variable, \
                 times,values, \
                 time_units,
                 ampl_units,
                 time_scale=1.0,
                 mag_scale=1.0):
        self.ampls = values
        self.times = times
        self.variable = variable
        self.time_scale = time_scale
        self.mag_scale = mag_scale
        self.time_units = time_units
        self.ampl_units = ampl_units

    @property
    def max_time(self):
        return max(self.times)


    def rec_time(self,t):
        if self.time_units == Waveform.TimeUnits.WALL_CLOCK_SECONDS:
            return t/self.time_scale
        else:
            return t*self.time_scale

    def rec_value(self,v):
        if self.ampl_units == Waveform.AmplUnits.VOLTAGE:
            return v/self.ampl_scale
        else:
            return v*self.ampl_scale

    @staticmethod
    def from_json(obj):
        return Waveform(variable=obj['variable'], \
                        times=obj['times'], \
                        values=obj['values'], \
                        time_units=Waveform.TimeUnits(obj['time_units']), \
                        ampl_units=Waveform.AmplUnits(obj['ampl_units']), \
                        time_scale=obj['time_scale'], \
                        mag_scale=obj['mag_scale'])

    def recover(self):
        times = list(map(lambda t: self.rec_time(t), self.times))
        values = list(map(lambda v: self.rec_value(v), self.values))

        return Waveform(variable=self.variable, \
                        times=times, \
                        value=values, \
                        time_units=self.time_units.rec_units(), \
                        ampl_units=self.ampl_units.rec_units(), \
                        time_scale=1.0/self.time_scale, \
                        mag_scale=1.0/self.mag_scale)


    def align(self,other):
        raise NotImplementedError
