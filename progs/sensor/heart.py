from dslang.dsprog import DSProg
from dslang.dssim import DSSim, DSInfo
import progs.sensor.sensor_util as sensor_util


def dsname():
  return "aheart"

def dsinfo():
  return DSInfo(dsname(), \
                "heartbeat model",
                "sensor output",
                "amplitude")
  info.nonlinear = True
  return info

# zeeman heart model with external pacemaker
def dsprog(prog):
  xd = 1.024
  xcontract = 0.4
  params = {"one":0.999999, \
            "eps":0.4, \
            "T": 1.0, \
            "xd": xd, \
            "xs": xd-xcontract, \
            "X0": xd, \
            "B0": 0.0
  }
  sensor_util.decl_external_input(prog,"U");
  params['ieps'] = 1.0/params['eps']
  params['Tieps'] = params['ieps']*params['T']
  params['nieps'] = -params['ieps']
  params['xds'] = params['xd'] - params['xs']
  params['nxd'] = -params['xd']
  dX = "{nieps}*X3 + {Tieps}*(X)  + {nieps}*(B)"
  dB = "{one}*X + {xds}*(U)"
  prog.decl_var("X3", "(X*X)*(X)")
  prog.decl_stvar("X", dX, "{X0}", params);
  prog.decl_stvar("B", dB, "{B0}", params);
  prog.emit("{one}*X","HEARTBEAT",params);
  # 7 khz
  tc = sensor_util.siggen_time_constant('heart-normal');
  #prog.speed(0.98*tc,tc*1.02)
  prog.interval("X",-3.0,3.0)
  prog.interval("B",-3.0,3.0)


def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .siggen_time('heart-normal'));
  dssim.real_time = True
  return dssim;
