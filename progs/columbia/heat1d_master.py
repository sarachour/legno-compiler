from dslang.dsprog import DSProg
from dslang.dssim import DSSim,DSInfo

N = 4
I = 2
WITH_GAIN = True



def make_dsname(N,I):
  return "heatN%dX%d" % (N,I)

def make_dsinfo(N,I):
  return DSInfo(make_dsname(N,I), \
                "movement of heat through %d point lattice" % N,
                "heat",
                "units")
  info.nonlinear = False
  return info


def make_dsprog(prog,N,I):
  h = 1.0/N
  tc = 1.0/(2*h)

  tc = 1.0
  nom = 0.9999999
  params = {
    'init_heat': 2.0,
    'one':nom,
    'tc':tc*nom
  }

  params['tc2'] = 2.0*tc

  for i in range(0,N):
    params["C"] = "D%d" % i
    # if there is no pervious (this is the first)
    params["P"] = "D%d" % (i-1) if i-1 >= 0 else None
    # if there is no next, this is the last
    params["N"] = "D%d" % (i+1) if i+1 < N else None

    if params['N'] is None:
        dPt = "{tc}*((-{C})+(-{C})+{P})"
        #dPt = "((-{C})+(-{C})+{P})"
    elif params['P'] is None:
        dPt = "{N} + (-{C}) + (-{C}) + {init_heat}"
        #dPt = "({N} + (-{C}) + (-{C}) + {init_heat})"
    else:
        dPt = "{P} + (-{C}) + (-{C}) + {N}"
        #dPt = "({P} + (-{C}) + (-{C}) + {N})"


    #prog.decl_stvar("D%d" % i, dPt, "0.0", params)
    prog.decl_stvar("D%d" % i, dPt, "0.0", params)
    prog.interval("D%d" % i, \
                  0, params['init_heat'])

  assert(I >= 1 and I <= N);
  prog.emit("{one}*D%d" % (I-1), "POINT",params)
  prog.max_time = 200
  prog.check()

def make_dssim():
  exp = DSSim('t120')
  exp.set_sim_time(120)
  return exp
