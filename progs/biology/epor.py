from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

def dsname():
  return "epor"

def dsinfo():
  info = DSInfo(dsname(), \
                "epor",
                "signal",
                "units")
  info.nonlinear = True
  return info


def dsprog(prog):
  params = {
    'p_kt':0.0329366,
    'p_Bmax':516.0,
    'p_kon':0.00010496,
    'p_koff':0.0172135,
    'p_ke':0.0748267,
    'p_kex':0.00993805,
    'p_kdi':0.00317871,
    'p_kde':0.0164042,
    'EpoR_0':516.0,
    'Epo_0': 2030.19,
    'EpoEpoR_0': 0,
    'EpoEpoRi_0': 0,
    'dEpoi_0':0,
    'dEpoe_0':0,
    'one':0.99999
  }
  params['p_kt_Bmax'] = params['p_kt']*params['p_Bmax']
  params['p_koff_ke'] = params['p_koff'] + params['p_ke']
  params['p_kex_kdi_kde'] = params['p_kex'] + params['p_kdi'] + params['p_kde']

  prog.decl_var('rr_46',"{p_koff}*EpoEpoR+{p_kex}*EpoEpoRi",params)
  prog.decl_var('rr_50', '{p_kon}*Epo*(-EpoR)',params)
  prog.decl_stvar('EpoR', \
                  'rr_46 + {p_kt_Bmax} + {p_kt}*(-EpoR) + rr_50', \
                  '{EpoR_0}',params);
  prog.interval("EpoR",0,516)

  prog.decl_stvar('Epo', \
                  'rr_46 + rr_50', \
                  '{Epo_0}',params)
  prog.interval("Epo",0,2031)

  prog.decl_stvar('EpoEpoR', '(-rr_50) + {p_koff_ke}*(-EpoEpoR)', \
                  '{EpoEpoR_0}', params)
  prog.interval('EpoEpoR',0,330)


  prog.decl_stvar('EpoEpoRi', '{p_ke}*EpoEpoR + {p_kex_kdi_kde}*(-EpoEpoRi)',\
                  '{EpoEpoRi_0}',params)
  prog.interval('EpoEpoRi',0,516)

  prog.decl_stvar('dEpoi', '{p_kdi}*EpoEpoRi', '{dEpoi_0}', params)
  prog.interval('dEpoi',0,250)

  prog.decl_stvar('dEpoe', '{p_kde}*EpoEpoRi', '{dEpoe_0}', params)
  prog.interval('dEpoe',0,800)
  prog.emit('{one}*EpoEpoR','measEpoEpoR',params)


def dssim():
  exp = DSSim('t100')
  exp.set_sim_time(100)
  return exp
