from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "bont4"

def dsinfo():
  info = DSInfo(dsname(), \
                "bont4",
                "signal",
                "units")
  info.nonlinear = False
  return info



def dsprog(prog):
  # original set of parameters
  params = {
    'r_bulk_kS': 1.5e-4*100.0,
    'r_endo_kT': 0.141,
    'r_trans_kL': 0.013,
    'r_bind_kB': 0.058,
    'freeB0': 0.0,
    'bndB0' : 0.0,
    'bulkB0' : 1.0,
    'transB0': 0.0,
    'lyticB0': 0.0,
    'one':0.999999
  }
  # reparametrization

  # functions

  base = 1.0
  b = 1.0*base
  dBulkB = '{r_bulk_kS}*(-bulkB)'
  prog.decl_stvar('bulkB',dBulkB,'{bulkB0}',params)
  prog.interval('bulkB',-b,b)


  b =0.2*base 
  dFreeB = '{r_bulk_kS}*bulkB + {r_bind_kB}*(-freeB)'
  prog.decl_stvar('freeB',dFreeB,'{freeB0}',params)
  prog.interval('freeB',-b,b)

  b = 0.03*base
  dBndB = '{r_bind_kB}*freeB + {r_endo_kT}*(-bndB)'
  prog.decl_stvar('bndB',dBndB, '{bndB0}',params)
  prog.interval('bndB',-b,b)

  b = 0.06*base
  dTransB = '{r_endo_kT}*bndB + {r_trans_kL}*(-transB)'
  prog.decl_stvar('transB',dTransB, '{transB0}',params)
  prog.interval('transB',-b,b)

  b = 0.004*base
  dLyticB = '{r_trans_kL}*transB'
  prog.decl_stvar('lyticB',dLyticB,'{lyticB0}',params)
  prog.interval('lyticB',-b,b)

  prog.emit('{one}*transB','MTRANSB',params)
  prog.check()

def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
