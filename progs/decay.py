from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo


def dsname():
  return "decay"

def dsinfo():
  info = DSInfo(dsname(), \
                desc="description",
                meas="observation name",
                units="observation units")
  info.nonlinear = False
  return info


def dsprog(prog):
  params = {'k':0.1,'x0':10.0}
  prog.decl_stvar("x","-{k}*x","{x0}",params)
  prog.emit('x','OBS')
  prog.interval('x',0,10.0)
  prog.check()
  return


def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
