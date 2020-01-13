from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo
import progs.prog_util as prog_util

def dsname():
  return "kalconst"

def dsinfo():
  info = DSInfo(dsname(), \
                "average tracking kalman filter",
                "average",
                "ampl")
  info.nonlinear = True
  return info

def dsprog(prog):
  params = {
    'meas_noise':1.0,
    'proc_noise':0.9999,
    'one':0.9999
  }

  ampl = 1.0
  freq = 0.3
  prog_util.build_oscillator(prog,ampl,freq,"dummy","SIG")
  params['Rinv'] = 1.0/params['proc_noise']
  params['nRinv'] = -1.0/params['proc_noise']
  params['X0'] = 0.0
  params['P0'] = 0.0
  params['Q'] = params['meas_noise']

  #E = "SIG+{one}*(-X)"
  E = "SIG+(-X)"
  dX = "{one}*RP*E"
  dP = "{Q}+(-RP)*P"


  prog.decl_var("RP","{Rinv}*P",params)
  prog.decl_var("E",E,params)
  prog.decl_stvar("X",dX,"{X0}",params)
  prog.decl_stvar("P",dP,"{P0}",params)
  prog.emit("{one}*X","STATE",params)
  prog.interval("X",-1.0,1.0)
  prog.interval("P",0,1.0)

def dssim():
  exp = DSSim('t50')
  exp.set_sim_time(50)
  return exp
