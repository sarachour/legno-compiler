import util.config as CONFIG
from compiler import srcgen
from hwlib.config import Config
from lab_bench.lib.chipcmd.use import *
import lab_bench.lib.command as cmd

import os

PROG = srcgen.GrendelProg()

def log(circ,block_name,loc,comp_mode,scale_mode):
  block = circ.board.block(block_name)
  if block.name == 'lut':
    return
  log_cfg = Config()
  log_cfg.set_scale_mode(scale_mode)
  log_cfg.set_comp_mode(comp_mode)
  if scale_mode is None:
    return

  srcgen.gen_block(PROG,circ,block,loc,log_cfg)

def is_empty():
  return len(PROG.stmts) == 0

def clear():
  PROG.clear()

def save(calib_mode):
  minprog = srcgen.GrendelProg()
  stmt_keys = []
  calib_file_pat = "{path}/{calib_obj}.grendel"
  calib_file = calib_file_pat.format(path=CONFIG.CALIBRATE_DIR, \
                                     calib_obj=calib_mode.value)

  if os.path.isfile(calib_file):
    with open(calib_file,'r') as fh:
      for line in fh:
        stmt = cmd.parse(line)
        stmt_keys.append(str(stmt))

  for stmt in PROG.stmts:
    if not isinstance(stmt, UseCommand):
      continue

    if str(stmt) in stmt_keys:
      continue

    minprog.add(stmt)
    stmt_keys.append(str(stmt))


  if os.path.exists(calib_file):
    lines = []
    with open(calib_file,'r') as fh:
      for line in fh:
        lines.append(line.strip())
  else:
    lines = []

  print("JAUNTLOG: logged %d stmts" % len(minprog.stmts))
  with open(calib_file,'w') as fh:
    for line in lines:
      fh.write("%s\n" % line)

    for stmt in minprog.stmts:
      stmt_str = str(stmt)
      if not stmt_str in lines:
        fh.write("%s\n" % stmt)
        lines.append(stmt_str)
