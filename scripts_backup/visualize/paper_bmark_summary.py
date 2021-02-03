import scripts.visualize.common as common
import numpy as np
import matplotlib.pyplot as plt
#import bmark.diffeqs as diffeq
from enum import Enum
import ops.op as op
from dslang.dsprog import DSProgDB


def visualize(db):
  header = ['description', 'observation','time','diffeqs','funcs','nonlinear']
  desc = 'dynamical system benchmarks used in evaluation. $\dagger$ these benchmarks '
  table = common.Table('Benchmarks',desc, 'bmarksumm', '|c|lccccc|')
  table.two_column = True
  bool_to_field = {True:'yes',False:'no'}
  table.set_fields(header)
  table.horiz_rule()
  table.header()
  table.horiz_rule()
  for bmark in table.benchmarks():
    bmark_name = bmark
    if 'heat1d' in bmark:
      bmark_name = 'heat1d'

    if not DSProgDB.has_prog(bmark):
      print("skipping %s... no info" % bmark)
      continue

    info = DSProgDB.get_info(bmark)
    prog = DSProgDB.get_prog(bmark)
    dssim = DSProgDB.get_sim(bmark)
    n_diffeqs = 0
    n_funcs = 0
    for v,bnd in prog.bindings():
      if bnd.op == op.OpType.INTEG:
        n_diffeqs += 1
      else:
        n_funcs += 1
    print(info)
    entry = {
      'description': info.description,
      'observation': info.observation,
      'diffeqs': n_diffeqs,
      'funcs': n_funcs,
      'time': str(dssim.sim_time) + " su",
      'nonlinear': bool_to_field[info.nonlinear]
    }
    table.data(bmark,entry)
  table.horiz_rule()

  table.write(common.get_path('bmarks.tbl'))
