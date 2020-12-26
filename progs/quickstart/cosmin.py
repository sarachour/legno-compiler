from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "cosmin"

def dsinfo():
  return DSInfo(dsname(), \
                "minimal cosine",
                "signal",
                "signal")
  info.nonlinear = True
  return info

def dsprog(prob):
  params = {
      'P0': 1.0,
      'V0' :0.0,
      'fact': 1.2/2.0
  }
  prob.decl_stvar("V","(-P)","{V0}",params)
  prob.decl_stvar("P","V","{P0}",params)
  prob.emit("{fact}*P","Position",params)
  prob.interval("P",-1.0,1.0)
  prob.interval("V",-1.0,1.0)

  coeff = params['fact']
  prob.interval("Position",-coeff*1.0,coeff*1.0)
  prob.check()
  return prob

def dssim():
  exp = DSSim('t50')
  exp.set_sim_time(50)
  return exp
