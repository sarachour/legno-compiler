from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "cos25"

def dsinfo():
  return DSInfo(dsname(), \
                "cosine",
                "signal",
                "signal")
  info.nonlinear = True
  return info

def dsprog(prob):
  params = {
    'P0': 10,
    'V0' :0.0
  }
  prob.decl_stvar("V","0.25*(-P)","{V0}",params)
  prob.decl_stvar("P","V","{P0}",params)
  prob.emit("P","Position")
  prob.interval("P",-10.0,10.0)
  prob.interval("V",-10.0,10.0)
  prob.check()
  return prob


def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
