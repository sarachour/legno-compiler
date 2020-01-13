from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo
import progs.sensor.sensor_util as sensor_util
import hwlib.units as units

def dsname():
  return "adenoise"

def dsinfo():
  return DSInfo(dsname(), \
                "denoise",
                "audio output",
                "amplitude")
  info.nonlinear = False
  return info


def dsprog(prog):
  params = {
    'meas_noise':1.0,
    'proc_noise':0.9999,
    'one':0.9999
  }
  params['Rinv'] = 1.0/params['proc_noise']
  params['nRinv'] = -1.0/params['proc_noise']
  params['X0'] = 0.0
  params['P0'] = 0.0
  params['Q'] = params['meas_noise']
  sensor_util.decl_external_input(prog,"SIG");
  E = "{one}*SIG+{one}*(-X)"
  dX = "{one}*RP*E"
  dP = "{Q}+{one}*(-RP)*P"
  prog.decl_var("RP","{Rinv}*P",params)
  prog.decl_var("E",E,params)
  prog.decl_stvar("X",dX,"{X0}",params)
  prog.decl_stvar("P",dP,"{P0}",params)
  prog.interval("X",-1.0,1.0)
  prog.interval("P",0,1.0)
  tc = sensor_util.siggen_time_constant('sin');
  prog.speed(0.95*tc,tc*1.05)
  prog.emit("{one}*X","STATE",params)


def dssim():
  dssim = DSSim('trc');
  dssim.set_sim_time(sensor_util \
                     .siggen_time('sin'));
  dssim.real_time = True
  return dssim;
