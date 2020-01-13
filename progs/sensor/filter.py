import progs.sensor.sensor_util as sensor_util
import progs.sensor.filter_util as filter_util
from dslang.dssim import DSSim
from dslang.dsprog import DSProg

def dsname():
  return "afilter"

def dsinfo():
  return DSInfo(dsname(), \
                "filter",
                "sensor output",
                "amplitude")
  info.nonlinear = False
  return info


def dsprog(prog):
  params = {
    "one": 0.99999
  }
  sensor_util.decl__input(prog,"X");
  cutoff_freq = 20000
  degree = 1
  out,model = filter_util.lpf(invar="X", \
                              outvar="Z", \
                              method=filter_util.FilterMethod.BASIC, \
                              cutoff_freq=cutoff_freq, \
                              degree=degree)

  filter_util.model_to_diffeqs(prog,model,1.0)
  prog.emit("{one}*%s" % out,"OUT",params);
  print(prog)
  input()

def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .wall_clock_time(0.1));
  dssim.set_hardware_env("sensor")
  return dssim;
