from dslang.dsprog import DSProg
from dslang.dssim import DSSim

def dsname():
  return "dbgdac"

def dsinfo():
  return DSInfo(dsname(), \
                "debug-dac",
                "signal",
                "signal")
  return info


def dsprog(prob):
  # dummy diffeq
  prob.decl_var("V","1.0")
  prob.emit("0.6*V","TestPoint")
  prob.check()

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
