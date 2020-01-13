from dslang.dsprog import DSProg
from dslang.dssim import DSSim
import progs.sensor.sensor_util as sensor_util

def dsname():
  return "adiv"

def dsinfo():
  return DSInfo(dsname(), \
                "scale signal",
                "sensor output",
                "amplitude")
  info.nonlinear = False
  return info


def dsprog(prog):
  params = {"one":0.999999,"coeff":0.5}
  sensor_util.decl_external_input(prog,"X");
  prog.decl_var("Y", "0.5*X");

  E = "Y+{one}*X*(-Z)"
  prog.decl_stvar("Z",E,"0.0",params)
  prog.interval("Z",0.0,4.0)
  prog.emit("{one}*Z","OUT",params);

def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .wall_clock_time(0.1));
  dssim.set_hardware_env("sensor")
  return dssim;
