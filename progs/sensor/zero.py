from dslang.dsprog import DSProg
from dslang.dssim import DSSim
import progs.sensor.sensor_util as sensor_util

def dsname():
  return "azero"

def dsinfo():
  return DSInfo(dsname(), \
                "zero signal",
                "sensor output",
                "amplitude")
  info.nonlinear = False
  return info


def dsprog(prog):
  params = {
    "one":0.99999
  }
  sensor_util.decl_external_input(prog,"X");
  prog.decl_var("Y", "{one}*X+{one}*(-X)",params);
  prog.interval("Y",-1,1)
  prog.emit("Y","OUT",params);

def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .wall_clock_time(0.1));
  return dssim;
