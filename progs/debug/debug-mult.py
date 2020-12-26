from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "dbgmult"

def dsinfo():
  return DSInfo(dsname(), \
                "debug mult",
                "signal",
                "signal")
  info.nonlinear = True
  return info

def dsprog(prob):
  params = {
    'P0': 1.0,
    'V0' :0.0,
    'fact': 1.2/2.0,
    'one':0.9999
  }
  prob.decl_stvar("V","(-P)","{V0}",params)
  prob.decl_stvar("P","V","{P0}",params)
  prob.decl_var("Q","{one}",params);
  prob.emit("{fact}*Q*P","Position",params,params)
  prob.interval("P",-1.0,1.0)
  prob.interval("V",-1.0,1.0)
  prob.check()
  return prob

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
