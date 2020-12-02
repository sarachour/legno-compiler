from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "vanderpol"

def dsinfo():
  info = DSInfo(dsname(), \
                "vanderpol oscillator",
                "signal",
                "amplitude")
  info.nonlinear = True
  return info

def dsprog(prog):
  params = {
    'mu': 0.2,
    'V0': 0.0,
    'U0': -0.5,
    'one':0.9999
  }
  dV = "({mu}*(V*(1.0+(-U)*U)) + {one}*(-U))"
  dU = "{one}*V"
  prog.decl_stvar("V",dV,"{V0}",params)
  prog.decl_stvar("U",dU,"{U0}",params)
  prog.emit("{one}*U","OSC",params)
  prog.interval("U",-2.5,2.5)
  prog.interval("V",-2.5,2.5)
  prog.check()
  return prog

def dssim():
  exp = DSSim('t50')
  exp.set_sim_time(50)
  return exp
