import hwlib.hcdc.globals as glb
import hwlib.units as units
import math

def decl_external_input(prog,name,chan1=True):
  prog.decl_extvar(name,loc='E1' if chan1 else 'E2');
  prog.interval(name,-1,1);
  prog.interval("EXT_%s" % name,-1,1)

def wall_clock_time(wall_time):
  return wall_time*glb.TIME_FREQUENCY

def siggen_time(name):
    # times in seconds, according to signal generator
    times = {
      'zero': 7*units.ms,
      'sin': 0.8*units.ms,
      'anomaly-ampl':0.8*units.ms,
      'anomaly-bias':0.8*units.ms,
      'kalman-bias':0.8*units.ms,
      'anomaly-freq':1.69*units.ms,
      'heart-normal':12.08*units.ms,
      'heart-irreg':12.08*units.ms,
    }
    return times[name];

def siggen_time_constant(name):
    freqs = {
      'sin': units.khz*40.0,
      'anomaly-freq': units.khz*40.0,
      'anomaly-ampl': units.khz*40.0,
      'anomaly-bias': units.khz*40.0,
      'kalman-bias': units.khz*40.0,
      'heart-normal': units.khz*2.5,
      'heart-irregular': units.khz*2.5
    }
    return time_constant(freqs[name])

def time_constant(freq):
    hwfreq = glb.TIME_FREQUENCY
    return freq/hwfreq
