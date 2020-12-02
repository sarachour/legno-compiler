from dslang.dsprog import DSProg
from dslang.dssim import DSSim, DSInfo
import progs.sensor.sensor_util as sensor_util
#import hwlib.units as units

def dsname():
  return "apower"

def dsinfo():
  return DSInfo(dsname(), \
                "power anomaly detector",
                "anomaly detected",
                "amplitude")
  info.nonlinear = True
  return info

'''
def ext(t):
    x =  math.sin(t)
    if t > 20 and t < 28:
        return math.sin(t)
    return x
def state_machine(z,t):
    u = ext(t)
    x,s,a = z
    dx = 0.4*u*u - 0.1*x
    ds = 0.1*x - 0.08*s
    da = s-x if a < 2.0 else 0
    return [dx,ds,da]
'''

def dsprog(prog):
  params = {
    "charge":0.6,
    "deg":0.8,
    "one":0.99999
  }

  IN = "{one}*U"
  dX = "{charge}*IN*IN + {deg}*(-X)"
  #ERROR = "X+{thresh}"
  sensor_util.decl_external_input(prog,"U");
  prog.decl_var("IN",IN,params)
  prog.decl_stvar("X",dX,"0.0",params)
  prog.interval("X",-1.0,1.0)
  prog.emit("{one}*X","DETECTOR",params);
  tau = sensor_util.siggen_time_constant('anomaly-ampl')
  prog.speed(tau*0.95,tau*1.05)


def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .siggen_time('anomaly-ampl'));
  dssim.real_time = True
  return dssim;
