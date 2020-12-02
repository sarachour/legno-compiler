from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo
import progs.sensor.sensor_util as sensor_util
#import hwlib.units as units

def dsname():
  return "abias"

def dsinfo():
  return DSInfo(dsname(), \
                "bias anomaly detector",
                "anomaly detected",
                "amplitude")
  info.nonlinear = True
  return info

def dsprog(prog):
  params = {
    "charge":0.3,
    "deg":0.8,
    'thresh':-0.1,
    "deltc":0.6,
    "one":0.99999
  }

  dX = "{charge}*U + {deg}*(-X)"
  #ERROR = "X+{thresh}"
  sensor_util.decl_external_input(prog,"U");
  prog.decl_stvar("X",dX,"0.0",params)
  #prog.decl_stvar("DEL1",dDEL1,"1.0",params)
  #prog.decl_stvar("DEL2",dDEL2,"1.0",params)
  #prog.decl_stvar("DEL3",dDEL3,"1.0",params)
  #prog.decl_var("ERROR",ERROR,params)
  '''
  TODO: debug threshold, end goal is to have sane trigger work.
  '''
  prog.interval("X",-1.0,1.0)
  #prog.interval("DEL1",-1.0,1.0)
  #prog.interval("DEL2",-1.0,1.0)
  #prog.interval("DEL1",0.0,1.0)
  #prog.emit("{one}*X","DETECTOR",params);
  prog.emit("{one}*X","DETECTOR",params);
  tau = sensor_util.siggen_time_constant('anomaly-bias')
  prog.speed(tau*0.95,tau*1.05)


def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .siggen_time('anomaly-bias'));
  dssim.real_time = True
  return dssim;
