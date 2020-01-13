from dslang.dsprog import DSProg
from dslang.dssim import DSSim, DSInfo
import progs.sensor.sensor_util as sensor_util

def dsname():
  return "apkalbias"

def dsinfo():
  return DSInfo(dsname(), \
                "passthru",
                "sensor output",
                "amplitude")
  info.nonlinear = False
  return info


def dsprog(prog):
  params = {
    'one':0.9999999
  }
  sensor_util.decl_external_input(prog,"X");
  prog.emit("X","OUT",params);

def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .siggen_time('kalman-bias'));
  dssim.real_time = True
  return dssim;
