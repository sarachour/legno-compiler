from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "dbgvga"

def dsinfo():
  return DSInfo(dsname(), \
                "debug vga",
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
  prob.decl_stvar("V","(-P)","{V0}",params)
  prob.decl_stvar("P","V","{P0}",params)
  prob.emit("{one}*P","Position",params)
  prob.interval("P",-1.0,1.0)
  prob.interval("V",-1.0,1.0)
  prob.check()
  return prob

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp

# 1.439614
# 1.411127
# 1.329994
