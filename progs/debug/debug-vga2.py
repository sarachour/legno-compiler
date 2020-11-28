from dslang.dsprog import DSProg
from dslang.dssim import DSSim

def dsname():
  return "dbgvga2"

def dsinfo():
  return DSInfo(dsname(), \
                "debug-mul",
                "signal",
                "signal")
  return info


def dsprog(prob):
  # dummy diffeq
  prob.decl_var("X","1.0")
  prob.decl_var("Z","0.3*X")
  prob.emit("Z","TestPoint")
  prob.check()

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
