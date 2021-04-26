from enum import Enum

import compiler.lwav_pass.waveform_align as alignutil
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.interpolate import interp1d
import numpy as np

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

    @property
    def npts(self):
        return len(self.times)


    def value(self,t):
        if t < self.min_time or t > self.max_time:
            raise Exception("time <%f> must be between %f and %f" \
                            % (t,self.min_time,self.max_time))

        return np.interp(t, self.times, self.values)

    @property
    def runtime(self):
        return self.max_time - self.min_time

    def start_from_zero(self):
        offset = min(self.times)
        Tnew = list(map(lambda t: t-offset, self.times))
        return Waveform(self.variable,Tnew,list(self.values), \
                        self.time_units,self.ampl_units, \
                        self.time_scale,self.mag_scale)


    def resample(self,npts):
        F = interp1d(self.times,self.values, \
                     fill_value='extrapolate')
        Tnew = np.linspace(min(self.times), max(self.times), \
                           num=npts)
        Xnew = F(Tnew)
        return Waveform(self.variable,Tnew,Xnew, \
                        self.time_units,self.ampl_units, \
                        self.time_scale,self.mag_scale)

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


    def error(self,other):
        start_time = max(min(self.times),min(other.times))
        end_time = min(max(self.times),max(other.times))
        npts = 200

        times = np.linspace(start_time,end_time,npts)
        sumsq = 0.0
        for t in times:
            v1 = self.value(t)
            v2 = other.value(t)
            sumsq += abs(v1-v2)**2

        return sumsq

    def apply_time_transform(self,scale,offset):
        xformed_times=list(map(lambda t: scale*t + offset, self.times))

        return Waveform(self.variable, \
                              times=xformed_times, \
                              values=self.values, \
                              ampl_units=self.ampl_units, \
                              time_units=self.time_units, \
                              mag_scale=self.mag_scale)


    def align(self,other,scale_slack=0.02, offset_slack=0.0001):
        if not (self.time_units == other.time_units):
            raise Exception("time unit mismatch: %s != %s"  \
                            % (self.time_units,other.time_units))
        if not (self.ampl_units == other.ampl_units):
            raise Exception("ampl unit mismatch: %s != %s"  \
                            % (self.ampl_units,other.ampl_units))

        npts = min(len(other), len(self))*2


        xform_spec = [
            (1.0-scale_slack,1.0+scale_slack),
            (-offset_slack,offset_slack)
        ]
        print("scaf times: [%s,%s]" \
              % (min(self.times),max(self.times)))

        print("sign times: [%s,%s]" \
              % (min(other.times),max(other.times)))
        xform,_ = alignutil.align(self.resample(npts), \
                                  other.resample(npts),xform_spec)
        xform['offset'] = -xform['offset']
        print(xform)
        print("limits: scale=%s offset=%s" % (xform_spec[0], xform_spec[1]))
        return xform,other.apply_time_transform(xform['scale'],xform['offset'])
 

    def __len__(self):
        return len(self.times)


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


    def set_style(self,name,color,linestyle,opacity=1.0):
        self.styles[name] = (color,linestyle,opacity)


    def plot(self,filepath):
        palette = sns.color_palette()
        ax = plt.subplot(1, 1, 1)
        title = self.title
        ax.tick_params(labelsize=24);
        ax.set_xlabel('time',fontsize=28)
        ax.set_ylabel(self.units,fontsize=28)
        ax.set_title(title,fontsize=32)
        ax.grid(False)

        ymax = ymin = 0.0
        for name,wf in self.waveforms.items():
            color,linestyle,opacity = self.styles[name]
            ax.plot(wf.times,wf.values,label=name,
                    linestyle=linestyle, \
                    linewidth=3, \
                    color=color, \
                    alpha=opacity)
            ymax = max(ymax,max(wf.values))
            ymin = min(ymin,min(wf.values))

        ax.set_ylim(ymin=ymin*1.1,ymax=ymax*1.1)

        plt.tight_layout()
        plt.savefig(filepath)
        plt.clf()

