from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo
import progs.prog_util as prog_util

def dsname():
  return "pid"

def dsinfo():
  return DSInfo(dsname(), \
                "PI controller",
                "velocity",
                "m/s")

def dsprog(prob):
  params = {
    "initial": 0.0,
    "one":0.99999
  }

  ampl = 1.0
  freq = 0.5
  prog_util.build_oscillator(prob,ampl,freq,"SIG","TARG")

  #params['negTarget'] = -params['target']
  PLANT = "CTRL+{one}"
  ERROR = "PLANT+{one}*(-TARG)"
  CONTROL = "2.0*(-ERR)+8.0*(-INTEG)"
  INTEGRAL = "{one}*ERR+0.3*(-INTEG)"

  #prob.decl_var("SIG",SIG,params)
  prob.decl_var("ERR",ERROR,params)
  prob.decl_var("CTRL",CONTROL,params)
  prob.decl_stvar("INTEG",INTEGRAL,"{initial}",params)
  prob.decl_stvar("PLANT",PLANT,"{initial}",params)

  prob.emit("{one}*PLANT","TrackedSig",params)
  #prob.emit("{one}*ERR","TrackingError",params)
  for v in ['PLANT','CTRL','ERR','INTEG']:
    prob.interval(v,-2.0,2.0)

  print(prob)
  prob.check()

def dssim():
  exp = DSSim('t200')
  exp.set_sim_time(200)
  return exp
