from dslang.dsprog import DSProg
from dslang.dssim import DSSim
import progs.sensor.sensor_util as sensor_util

def dsname():
  return "ascale"

def dsinfo():
  return DSInfo(dsname(), \
                "scale signal",
                "sensor output",
                "amplitude")
  info.nonlinear = False
  return info


def dsprog(prog):
  sensor_util.decl_external_input(prog,"X");
  prog.decl_var("Y", "0.5*X");
  prog.emit("Y","OUT");

def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .siggen_time('sin'));
  return dssim;
