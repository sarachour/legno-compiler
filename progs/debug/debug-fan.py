from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "dbgfan"

def dsinfo():
  return DSInfo(dsname(), \
                "debug-fan",
                "signal",
                "signal")
  return info


def dsprog(prob):
  # dummy diffeq
  prob.decl_var("V","1.0")
  prob.emit("0.6*(V-V)","TestPoint")
  prob.check()

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
