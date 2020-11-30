from dslang.dsprog import DSProg
from dslang.dssim import DSSim

def dsname():
  return "dbgadc"

def dsinfo():
  return DSInfo(dsname(), \
                "debug adc",
                "signal",
                "signal")
  info.nonlinear = True
  return info

def dsprog(prob):
  params = {
    'P0': 1.0,
    'V0' :0.0,
    'one':0.9999
  }
  prob.decl_lambda("ident","sgn(X)*sqrt(abs(X))")
  prob.decl_var("Q","emit(ident(P))")
  prob.decl_var("P","0.5")
  prob.interval("P",-1.0,1.0)
  prob.check()
  return prob

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp

# 1.439614
# 1.411127
# 1.329994
