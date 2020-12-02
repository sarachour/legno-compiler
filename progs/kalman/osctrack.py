from dslang.dsprog import DSProg
from dslang.dssim import DSSim
import progs.sensor.sensor_util as sensor_util
#import hwlib.units as units


def dsname():
  return "akalosc"

def dsinfo():
  return DSInfo(dsname(), \
                "bias anomaly detector",
                "anomaly detected",
                "amplitude")
  info.nonlinear = True
  return info

def dsprog(prog):
  params = {
    'meas_noise':0.3,
    'proc_noise':0.5,
    'X0':1.0,
    'V0':0.0,
    'P0':1.0,
    'one':0.9999
  }
  params['Q'] = params['meas_noise']
  params['Rinv'] = 1.0/params['proc_noise']
  params['nRinv'] = -1.0/params['proc_noise']

  dX = "{one}*V + {Rinv}*P11*E"
  dV = "{one}*(-X) + {Rinv}*P12*E"
  dP11 = "2.0*P12 + {Q} + {nRinv}*P11*P11"
  dP12 = "{one}*P22+{one}*(-P11) +{Q} + {nRinv}*P11*P12"
  dP22 = "2.0*(-P12) + {Q} + {nRinv}*P12*P12"

  sensor_util.decl_external_input(prog,"U");
  prog.decl_var("E","{one}*U+{one}*(-X)",params)
  prog.decl_stvar("X",dX,"{X0}",params)
  prog.decl_stvar("V",dV,"{V0}",params)
  prog.decl_stvar("P11",dP11,"{P0}",params)
  prog.decl_stvar("P12",dP12,"{P0}",params)
  prog.decl_stvar("P22",dP22,"{P0}",params)
  prog.emit("{one}*X","MODEL",params)

  prog.interval("X",-1.0,1.0)
  prog.interval("V",-1.0,1.0)
  prog.interval("W",-1.0,1.0)
  for cov in ['11','12','22']:
    prog.interval("P%s" % cov,-1.2,1.2)


def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .siggen_time('anomaly-freq'));
  dssim.real_time = True
  return dssim;
