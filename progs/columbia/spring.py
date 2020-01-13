from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "spring"

def dsinfo():
  info = DSInfo(dsname(), \
                "two-mass spring system",
                "mass 1",
                "position")
  info.nonlinear = True
  return info

def dsprog(prog):
  k = 0.5
  cf= 0.15

  params = {
    'k1': k,
    'k2': k,
    'k3': k,
    'cf': cf,
    'PA0': 2.0,
    'VA0': 0,
    'PB0': -1.0,
    'VB0': 0,
    'one':0.99999
  }
  params['k1_k2'] = (params['k1'] + params['k2'])*0.99999
  params['k2_k3'] = (params['k3'] + params['k2'])*0.99999

  fPA = 'force(PA)'
  fPB = 'force(PB)'
  dVA = '{k2}*fPB + {k1_k2}*(-fPA)+{cf}*(-VA)'
  dVB = '{k2}*fPA + {k2_k3}*(-fPB)+{cf}*(-VB)'
  dPA = 'VA'
  dPB = 'VB'
  prog.decl_lambda("force","sgn(T)*sqrt(abs(T))");
  prog.decl_var("fPA",fPA,params)
  prog.decl_var("fPB",fPB,params)
  prog.decl_stvar("VA",dVA,"{VA0}",params)
  prog.decl_stvar("VB",dVB,"{VB0}",params)
  prog.decl_stvar("PA",dPA,"{PA0}",params)
  prog.decl_stvar("PB",dPB,"{PB0}",params)

  prog.emit("{one}*PA","PosA",params)
  prog.interval("PA",-2.5,2.5)
  prog.interval("PB",-2.5,2.5)
  prog.interval("VA",-2.5,2.5)
  prog.interval("VB",-2.5,2.5)
  prog.check()

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
