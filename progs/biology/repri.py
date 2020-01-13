from dslang.dsprog import DSProg
from dslang.dssim import DSSim, DSInfo
import progs.prog_util as prog_util

def dsname():
  return "repri"

def dsinfo():
  return DSInfo(dsname(), \
                "rep",
                "signal",
                "signal")
  info.nonlinear = True
  return info


def dsprog(prob):
  K = 20.0
  params = {
    'LacLm0':0.5,
    'clm0':0.25,
    'TetRm0':0.12,
    'LacLp0':60.0,
    'clp0':20.0,
    'TetRp0':40.0,
    'K':K,
    'n':2.0,
    'a_tr':0.4995,
    'kd_mrna' : 0.15051499783,
    'a0_tr':0.0005,
    'k_tl': 3.01029995664,
    'kd_prot': 0.03010299956,
    'one': 0.9999999,
    'mrna_bnd':3.0,
    'prot_bnd':140.0
  }

  # reparametrization
  K = 0.70
  #scale = 1.1
  scale = 5.1
  params = {
    'LacLm0':0.5,
    'clm0':0.25,
    'TetRm0':0.12,
    'LacLp0':0.6,
    'clp0':0.2,
    'TetRp0':0.4,
    'K':K,
    'n':2.0,
    'a_tr':0.99,
    'kd_mrna' : 0.20,
    'k_tl': 0.201029995664,
    'kd_prot': 0.30,
    'one': 0.9999999,
    'mrna_bnd':1.3*scale,
    'prot_bnd':0.85*scale,
    'gene_bnd':1.0*scale
  }
  closed_form = True;

  prob.decl_stvar("LacLm",'{a_tr}*ALacL+{kd_mrna}*(-LacLm)',"{LacLm0}",params)
  prob.decl_stvar("clm",'{a_tr}*Aclp+{kd_mrna}*(-clm)',"{clm0}",params)
  prob.decl_stvar("TetRm",'{a_tr}*ATetR+{kd_mrna}*(-TetRm)',"{TetRm0}", params)

  mrna_bnd = params['mrna_bnd']
  prob.interval("LacLm",0,mrna_bnd)
  prob.interval("clm",0,mrna_bnd)
  prob.interval("TetRm",0,mrna_bnd)

  prob.decl_stvar("LacLp",'{k_tl}*LacLm + {kd_prot}*(-LacLp)',"{LacLp0}",params)
  prob.decl_stvar("clp",'{k_tl}*clm + {kd_prot}*(-clp)',"{clp0}",params)
  prob.decl_stvar("TetRp",'{k_tl}*TetRm + {kd_prot}*(-TetRp)',"{TetRp0}",params)

  prot_bnd = params['prot_bnd']
  prob.interval("LacLp",0,prot_bnd)
  prob.interval("clp",0,prot_bnd)
  prob.interval("TetRp",0,prot_bnd)

  K = params['K']
  n = params['n']

  def mkrxn(prot,name):
    subparams = {
      'Kd': 1.0/(K**n),
      'speed':4.0
    }
    subparams['kf'] = subparams['Kd']*subparams['speed']
    subparams['kr'] = params['one']*subparams['speed']
    subparams['L0'] = 1.0
    subparams['L'] = "A%s" % name
    subparams['P'] = prot
    subparams['one'] = 0.9999999
    subparams['krL0'] = subparams['kr']*subparams['L0']
    #expr = "{kr}*(-{L}) + {kf}*{P}*({P}*(-{L}))"
    expr = "{krL0} + {kr}*(-{L}) + {kf}*({one}*({P}*({one}*{P})))*(-{L})"
    prob.decl_stvar(subparams["L"],expr,"{L0}",subparams)
    prob.interval(subparams["L"],0,subparams["L0"])

  #mkrxn(prot="clp",name="LacL")
  #mkrxn(prot="LacLp",name="TetR")
  #mkrxn(prot="TetRp",name="clp")

  params["Kn"] = params["K"]**params["n"]
  prob.decl_lambda("bind","({Kn})/({Kn}+max(P,0)^2)",params)
  prob.decl_var("ALacL","bind(clp)",params)
  prob.decl_var("ATetR","bind(LacLp)",params)
  prob.decl_var("Aclp","bind(TetRp)",params)
  act_bnd = params['gene_bnd']
  prob.interval("ALacL",0,act_bnd)
  prob.interval("ATetR",0,act_bnd)
  prob.interval("Aclp",0,act_bnd)
  prob.emit("{one}*LacLp","LacLProt",params)


def dssim():
  sim = DSSim("t200")
  sim.set_sim_time(200)
  return sim
