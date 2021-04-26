from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo
import progs.prog_util as prog_util


def dsname():
  return "gentog"

def dsinfo():
  info = DSInfo(dsname(), \
                'genetic toggle switch',
                "[V]",
                "conc")
  info.nonlinear = True
  return info



def dsprog(prog):
  K = 1.0
  params = {
    'a2': 15.6,
    #'a1': 156.25,
    'a1': 15.62,
    #'K' : 0.000029618,
    'K' : K,
    'nu': 2.0015,
    'beta': 2.5,
    'gamma': 1.0,
    'U0': 0.0,
    'V0': 0.0,
    'kdeg': 0.99999999,
    'one':0.99999
  }
  #reparametrization
  # derived parameters
  params['invK'] = 1.0/params['K']
  params['negNu'] = -params['nu']
  params['one'] = 0.999999
  params['halfK'] = K/2.0;
  ampl = params['halfK']
  freq = 0.9999999
  prog_util.build_oscillator(prog,ampl,freq,"VPERT","PERT")

  prog.decl_var("IPTG", "{halfK} + PERT",params)
  #prog.decl_lambda("umod","(1+max(X,0)*{invK})^{negNu}",params)
  prog.decl_lambda("utf", "{a1}/(1+max(X,0)^{beta})",params)
  prog.decl_lambda("vtf", "{a2}/(1+max(X,0)^{gamma})",params)
  prog.decl_lambda("umod","(1+max(X,0)*{invK})^{negNu}",params)

  prog.decl_lambda("umodvtf", "{a2}/(1+max(((1+max(X,0)*{invK})^{negNu}),0)^{gamma})",params)


  #prog.decl_var("FNUMOD", "umod(IPTG)",params)
  #prog.interval("FNUMOD",0,1.2)
  #prog.decl_var("UMODIF", "U*({one}*FNUMOD)",params)
  #prog.interval("UMODIF",0,0.40)

  prog.decl_var("UMOD", "umod(IPTG)",params)
  prog.interval("UMOD",0.0,1.0)
  prog.decl_var("UTF", "utf(V)",params)
  prog.interval("UTF",0.0,16.0)
  prog.decl_var("VTF", "vtf((U*UMOD))",params)
  prog.interval("VTF",0.0,16.0)

  dV = "{one}*VTF + {kdeg}*(-V)"
  dU = "{one}*UTF + {kdeg}*(-U)"

  # this is a dummy output so that we can flip the sign.
  #prog.decl_var("fU","U");
  prog.decl_stvar("V",dV, "{V0}", params);
  prog.decl_stvar("U",dU, "{U0}", params);
  prog.emit("{one}*V", "compV", params)

  prog.interval("V",0,16.0)
  prog.interval("U",0,1.2)
  return


def dssim():
  exp = DSSim('t20')
  exp.set_sim_time(20)
  return exp
