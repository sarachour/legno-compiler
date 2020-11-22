from enum import Enum

class Waveform:
    class TimeUnits(Enum):
        WALL_CLOCK_SECONDS = "wall_clock_sec"
        DS_TIME_UNITS = "ds_time_units"

    class AmplUnits(Enum):
        VOLTAGE = "voltage"
        DS_QUANTITY = "ds_quantity"

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

    @property
    def rec_max_time(self):
        if self.time_units == Waveform.TimeUnits.WALL_CLOCK_SECONDS:
            return self.max_time/self.time_scale
        else:
            return self.max_time*self.time_scale

    @staticmethod
    def from_json(obj):
        return Waveform(variable=obj['variable'], \
                        times=obj['times'], \
                        values=obj['values'], \
                        time_units=Waveform.TimeUnits(obj['time_units']), \
                        ampl_units=Waveform.AmplUnits(obj['ampl_units']), \
                        time_scale=obj['time_scale'], \
                        mag_scale=obj['mag_scale'])
