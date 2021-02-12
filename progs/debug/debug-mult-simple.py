from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "dbgmult-simpl"

def dsinfo():
  return DSInfo(dsname(), \
                "debug-mult-simple",
                "signal",
                "signal")
  return info


def dsprog(prob):
  # dummy diffeq
  prob.decl_var("V","1.0")
  prob.decl_var("Z","V*V")
  prob.emit("0.6*Z","TestPoint")
  prob.check()

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
