from dslang.dsprog import DSProg
from dslang.dssim import DSSim, DSInfo


def dsinfo():
  return DSInfo(dsname(), \
                "lotka-voltera system",
                "population",
                "thou")

def dsname():
  return "lotka"


def dsprog(prog):
  params = {
    'rabbit_spawn':0.3,
    'fox_death': 0.2,
    'rabbit_kill': 0.8,
    'fox_reproduce': 0.50,
    "fox_init": 1.0,
    "rabbit_init": 1.0,
    'one':0.999999
  }
  params['fox_spawn'] = params['fox_reproduce']*params['rabbit_kill']

  dRabbit = "{rabbit_spawn}*RABBIT + {rabbit_kill}*(-FIGHT)"
  dFox = "{fox_spawn}*FIGHT + {fox_death}*(-FOX)"
  prog.decl_stvar("RABBIT",dRabbit,"{rabbit_init}",params)
  prog.decl_stvar("FOX",dFox,"{fox_init}",params)
  prog.decl_var("FIGHT","(FOX*RABBIT)",params)

  prog.emit("{one}*RABBIT","RabbitPop",params)
  rabbit_ival = 2.0
  fox_ival = 1.4
  prog.interval("RABBIT",0,rabbit_ival)
  prog.interval("FOX",0,fox_ival)
  prog.check()


def dssim():
  exp = DSSim('t200')
  exp.set_sim_time(200)
  return exp
