from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo
import progs.prog_util as prog_util

def dsname():
  return "forced"

def dsinfo():
  info = DSInfo(dsname(), \
                "forced vanderpol oscillator",
                "signal",
                "amplitude")
  info.nonlinear = True
  return info

def dsprog(prog):
  rel_time = 5.0
  mu = 0.2
  params = {
    'mu': rel_time*mu,
    'Y0': 0.0,
    'X0': -0.5,
    'one':0.9999,
    'tc':1.0*rel_time
  }
  ampl,freq = 1.0,1.0
  prog_util.build_oscillator(prog,freq,ampl,"DUMMY","W")

  dY = '{tc}*W+Y*{mu}*(1.0+(-X)*X)+{tc}*(-X)'
  dX = '{tc}*Y'

  prog.decl_stvar("Y",dY,"{Y0}",params)
  prog.decl_stvar("X",dX,"{X0}",params)
  prog.emit("{one}*X","OSC",params)
  prog.interval("X",-2.2,2.2)
  prog.interval("Y",-2.2,2.2)
  prog.check()
  return prog

def dssim():
  exp = DSSim('t50')
  exp.set_sim_time(50)
  return exp
