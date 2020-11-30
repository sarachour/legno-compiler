from enum import Enum

import compiler.lwav_pass.waveform_align as alignutil
import matplotlib.pyplot as plt
import seaborn as sns

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
        self.values = values
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
    def min_time(self):
        return min(self.times)


    def trim(self,min_time,max_time):
        start = 0
        for i,t in enumerate(self.times):
            if t >= min_time:
                start = i
                break;

        end = len(self.times)
        for i,t in enumerate(self.times):
            if t > max_time:
                end = i
                break;

        self.times = self.times[start:end]
        self.values = self.values[start:end]

    def rec_time(self,t):
        base = 1.0/126000
        if self.time_units == Waveform.TimeUnits.WALL_CLOCK_SECONDS:
            return t/self.time_scale
        else:
            return t*self.time_scale

    def rec_value(self,v):
        if self.ampl_units == Waveform.AmplUnits.VOLTAGE:
            return v/self.mag_scale
        else:
            return v*self.mag_scale

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
                        values=values, \
                        time_units=self.time_units.rec_units(), \
                        ampl_units=self.ampl_units.rec_units(), \
                        time_scale=1.0/self.time_scale, \
                        mag_scale=1.0/self.mag_scale)


    def align(self,other):
        if not (self.time_units == other.time_units):
            raise Exception("time unit mismatch: %s != %s"  \
                            % (self.time_units,other.time_units))
        if not (self.ampl_units == other.ampl_units):
            raise Exception("ampl unit mismatch: %s != %s"  \
                            % (self.ampl_units,other.ampl_units))

        #time_slack = 0.02
        time_slack = 0.04
        time_jitter = other.max_time*0.1
        xform_spec = [
            (1.0-time_slack,1.0+time_slack),
            #(0.0,max(tmeas)*0.25)
            (-time_jitter,time_jitter)
        ]
        return alignutil.align(self,other,xform_spec)






class WaveformVis:

    def __init__(self,name,units,title):
        self.name = name
        self.units = units
        self.title = title
        self.waveforms = {}
        self.styles = {}
 
    @property
    def time_units(self):
        for wf in self.waveforms.values():
            return wf.time_units
        return None

    @property
    def num_waveforms(self):
        return len(self.waveforms.keys())

    @property
    def empty(self):
        return self.num_waveforms == 0

    def add_waveform(self,name,wf):
        if not self.empty and \
           self.time_units != wf.time_units:
            raise Exception("time unit mismatch: %s != %s (%d)" \
                            % (self.time_units,wf.time_units, self.num_waveforms))

        self.waveforms[name] = wf


    def set_style(self,name,color,linestyle):
        self.styles[name] = (color,linestyle)


    def plot(self,filepath):
        palette = sns.color_palette()
        ax = plt.subplot(1, 1, 1)
        title = self.title
        ax.tick_params(labelsize=16);
        ax.set_xlabel('simulation time',fontsize=32)
        ax.set_ylabel(self.units,fontsize=32)

        ax.grid(False)

        for name,wf in self.waveforms.items():
            color,linestyle = self.styles[name]
            ax.plot(wf.times,wf.values,label=name,
                    linestyle=linestyle, \
                    linewidth=3, \
                    color=color)

        #plt.tight_layout()
        plt.savefig(filepath)
        plt.clf()

