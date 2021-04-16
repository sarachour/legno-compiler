from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo
import progs.prog_util as prog_util

def dsname():
  return "kalsmooth"

def dsinfo():
  info = DSInfo("kalman", \
                "average tracking kalman filter",
                "average",
                "amplitude")
  info.nonlinear = True
  return info

def dsprog(prog):
  params = {
    'meas_noise':0.6,
    'proc_noise':2.0,
    'one':0.9999
  }

  ampl = 0.7
  freq = 0.2
  prog_util.build_oscillator(prog,ampl,freq,"VSIG","SIG")

  ampl = 0.3
  freq = 3.0
  #prog_util.build_oscillator(prog,ampl,freq,"VNZ","NZ")



  params['Rinv'] = 1.0/params['proc_noise']
  params['X0'] = 0.0
  params['P0'] = 0.0
  params['Q'] = params['meas_noise']

  #prog.decl_var("INP", "SIG+NZ")
  #E = "INP+(-X)"

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
  exp = DSSim('t100')
  exp.set_sim_time(100)
  return exp
