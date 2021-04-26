from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo
import progs.prog_util as prog_util


def dsname():
  return "smmrxn"

def dsinfo():
  info = DSInfo(dsname(), \
                "michaelis menten reaction",
                "[ES]",
                "conc")
  info.nonlinear = True
  return info


def dsprog(prog):
  params = {
    'E0': 0.8,
    'S0': 0.5,
    'ES0': 0.0,
    'kf': 0.9999,
    'kr': 0.3,
    'one': 0.9999
  }

  dES = "{kf}*(E*S) + {kr}*(-ES)"
  prog.decl_var("E", "{E0} + (-ES)", params);
  prog.decl_var("S", "{S0} + (-ES)", params);
  prog.decl_stvar("ES", dES, "{ES0}", params)
  prog.emit("{one}*ES", "COMPLEX",params)
  max_ES = min(params['E0'],params['S0'])

  prog.interval("E",0,params['E0'])
  prog.interval("S",0,params['S0'])
  prog.interval("ES",0,max_ES)
  prog.check()


def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
