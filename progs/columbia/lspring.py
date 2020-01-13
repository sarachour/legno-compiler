from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "lspring"

def dsinfo():
  return DSInfo(dsname(), \
                "linear two-mass spring system",
                "mass 1",
                "position")
  info.nonlinear = False
  return info

def dsprog(prog):
  k = 0.5
  cf= 0.15
  params = {
    'k1': k,
    'k2': k,
    'k3': k,
    'cf': -cf,
    'PA0': 2.0,
    'VA0': 0,
    'PB0': -1.0,
    'VB0': 0,
    'one':0.9999
  }
  params['k1_k2'] = -(params['k1'] + params['k2'])*0.999
  params['k2_k3'] = -(params['k3'] + params['k2'])*0.999

  dVA = '{k2}*PB + {k1_k2}*PA+{cf}*VA'
  dVB = '{k2}*PA + {k2_k3}*PB+{cf}*VB'
  dPA = '{one}*VA'
  dPB = '{one}*VB'
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
