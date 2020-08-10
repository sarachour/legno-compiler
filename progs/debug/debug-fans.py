from dslang.dsprog import DSProg
from dslang.dssim import DSSim

def dsname():
  return "dbgfans"

def dsinfo():
  return DSInfo(dsname(), \
                "debug adc",
                "signal",
                "signal")
  return info

def dsprog(prob):
  params = {
    'P0': 1.0,
    'V0' :0.0,
    'one':0.9999
  }
  for i in range(0,24):
    prob.decl_stvar("V%d" % i,"(-P)","{V0}",params)
    prob.interval("V%d" % i,-1.0,1.0)
  prob.decl_stvar("P","V0","{P0}",params)
  prob.emit("P","Position",params)
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
