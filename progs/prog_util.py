

def build_oscillator(prog,ampl,freq,vname,pname):
  params = {
    "alpha":freq*freq,
    "P0":ampl,
    "V0":0.0,
    "POS":pname,
    "VEL":vname
  }

  if freq != 1.0:
    dVel = "{alpha}*(-{POS})"
  else:
    dVel = "(-{POS})"

  dPos = "{VEL}"

  prog.decl_stvar(pname,dPos,"{P0}",params)
  prog.decl_stvar(vname,dVel,"{V0}",params)

  tc = freq
  prog.interval(pname,-ampl,ampl)
  prog.interval(vname,-ampl*tc,ampl*tc)
