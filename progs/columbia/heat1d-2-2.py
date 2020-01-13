import progs.columbia.heat1d_master as heat1d


N = 2
I = 2

def dsname():
  return heat1d.make_dsname(N,I)

def dsinfo():
  return heat1d.make_dsinfo(N,I)


def dsprog(prog):
  return heat1d.make_dsprog(prog,N,I)

def dssim():
  return heat1d.make_dssim()
