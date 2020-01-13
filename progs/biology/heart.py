from dslang.dsprog import DSProg
from dslang.dssim import DSSim, DSInfo
import progs.sensor.sensor_util as sensor_util
import progs.prog_util as prog_util


def dsname():
  return "heart"

def dsinfo():
  return DSInfo(dsname(), \
                "heartbeat model",
                "sensor output",
                "amplitude")
  info.nonlinear = True
  return info

# zeeman heart model with external pacemaker
def dsprog(prog):
  params = {"one":0.999999, \
            "eps":0.4, \
            "T": 1.0, \
            "xd": 1.024, \
            "xs": 0.4, \
            "X0": 1.025, \
            "B0": 0.0
  }

  ampl = 1.0
  freq = 0.5
  prog_util.build_oscillator(prog,ampl,freq,"dummy","U")
  params['ieps'] = 1.0/params['eps']
  params['Tieps'] = params['ieps']*params['T']
  params['nieps'] = -params['ieps']
  params['xds'] = params['xd'] - params['xs']
  params['nxd'] = -params['xd']
  dX = "{nieps}*X3 + {ieps}*(X)  + {nieps}*(B)"
  dB = "{one}*X + {nxd} + {xds}*U*U"
  prog.decl_var("X3", "(X*X)*(X)")
  prog.decl_stvar("X", dX, "{X0}", params);
  prog.decl_stvar("B", dB, "{B0}", params);
  prog.emit("{one}*X","HEARTBEAT",params);
  # 4.37 khz
  prog.interval("X",-3.0,3.0)
  prog.interval("B",-3.0,3.0)


def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(200);
  return dssim;
