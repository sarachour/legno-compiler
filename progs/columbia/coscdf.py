from dslang.dsprog import DSProg
from dslang.dssim import DSSim

def dsname():
  return "coscdf"

def dsprog(prog):
  params = {
    'V0': -2,
    'P0': 9,
    'one':0.9999
  }
  # making P' = 1*V breaks the frequency.
  prog.decl_stvar("V","0.22*(-V)+0.84*(-P)","{V0}",params)
  #prog.decl_stvar("P","{one}*V","{P0}",params)
  prog.decl_stvar("P","{one}*V","{P0}",params)
  prog.emit("{one}*P","Position",params)
  prog.interval("P",-10.0,10.0)
  prog.interval("V",-10.0,15.0)
  prog.check()
  return prog

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
