from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "cos"

def dsinfo():
  return DSInfo(dsname(), \
                "cosine",
                "signal",
                "signal")
  info.nonlinear = True
  return info

def dsprog(prob):
  params = {
    'P0': 1.0,
    'V0' :0.0
  }
  # V' = -P
  # V(0) = params['V0']
  prob.decl_stvar("V","(-P)","{V0}",params)
  # P' = V
  # P(0) = params['P0']
  prob.decl_stvar("P","V","{P0}",params)
  # please measure 0.6*P
  prob.emit("0.6*P","Position")
  #
  prob.interval("P",-1.0,1.0)
  prob.interval("Position",-1.0,1.0)
  prob.interval("V",-1.0,1.0)
  prob.check()
  return prob

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
