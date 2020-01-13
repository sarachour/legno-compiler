import os
import time
import matplotlib.pyplot as plt

from scripts.expdriver_db import ExpDriverDB
from scripts.common import ExecutionStatus
import lab_bench.lib.command as cmd

from hwlib.adp import AnalogDeviceProg

import scripts.analysis.params as params
import scripts.analysis.quality as quality
import scripts.analysis.energy as energy

import tqdm

#board = make_board('standard')

BOARD_CACHE = {}

def execute_once(args,debug=False):
  db = ExpDriverDB()
  

  entries = list(db.experiment_tbl.get_by_status(ExecutionStatus.RAN))
  if args.include_pending:
    entries += list(db.experiment_tbl \
                 .get_by_status(ExecutionStatus.PENDING))

  for entry in tqdm.tqdm(entries):
    if not entry.runtime is None \
      and (not entry.quality is None and not args.recompute_quality)\
      and not entry.energy is None:
      continue


    if not args.prog is None and not entry.program == args.prog:
      continue

    if not args.subset is None and not entry.subset == args.subset:
      continue

    if not args.model is None and entry.model != args.model:
      continue

    if not args.obj is None and entry.obj != args.obj:
      continue

    board = None
    if not os.path.isfile(entry.adp):
      continue

    if entry.energy is None or entry.runtime is None or \
       args.recompute_params:
      if not entry.subset in BOARD_CACHE:
        from hwlib.hcdc.hcdcv2_4 import make_board
        board = make_board(entry.subset,load_conns=False)
        BOARD_CACHE[entry.subset] = board
      else:
        board = BOARD_CACHE[entry.subset]
      ad_prog = AnalogDeviceProg.read(board,entry.adp)
      params.analyze(entry,ad_prog)
      energy.analyze(entry,ad_prog)
    
    if entry.status != ExecutionStatus.PENDING and \
            (entry.quality is None or args.recompute_quality):
      ad_prog = AnalogDeviceProg.read(None,entry.adp)

      quality.analyze(entry, \
                      recompute=args.recompute_quality)

  db.close()

def rank(entry,debug=False):
  board = None
  if not entry.subset in BOARD_CACHE:
        from hwlib.hcdc.hcdcv2_4 import make_board
        board = make_board(entry.subset,load_conns=False)
        BOARD_CACHE[entry.subset] = board

  board = BOARD_CACHE[entry.subset]
  ad_prog = AnalogDeviceProg.read(board,entry.adp)
  for block_name,loc,config in ad_prog.instances():
    if block_name == "integrator":
      scf = config.scf("out")
      ival = config.interval("out")
      props = board.block(block_name).props(config.comp_mode, \
                                            config.scale_mode,"out")

      score = scf*ival.bound/props.interval().bound
      print(scf,score)
  input()


def execute(args,debug=False):
  daemon = args.monitor
  if not daemon:
    execute_once(args,debug=debug)
  else:
    while True:
      execute_once(args,debug=debug)
      print("...")
      time.sleep(10)
