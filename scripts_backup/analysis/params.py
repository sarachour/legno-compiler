from enum import Enum
from dslang.dsprog import DSProgDB

def update_experiment_params(ad_prog,exper_entry):
  dssim = DSProgDB.get_sim(exper_entry.program)
  tc = ad_prog.board.time_constant*ad_prog.tau
  runtime = dssim.sim_time/tc
  exper_entry.runtime = runtime

def update_output_params(ad_prog, \
                  output_entry):
  LOCS = []
  for block_name,loc,config in ad_prog.instances():
    handle = ad_prog.board.handle_by_inst(block_name,loc)
    if handle is None:
      continue

    for port,label,label_kind in config.labels():
      if label == output_entry.variable:
        LOCS.append((block_name,loc,port,handle))

  if len(LOCS) == 0:
    print(output_entry)
    raise Exception("cannot find measurement port")

  if (len(LOCS) > 1):
    raise Exception("more than one port with that label")

  block_name,loc,port,handle = LOCS[0]
  cfg = ad_prog.config(block_name,loc)
  dssim = DSProgDB.get_sim(output_entry.program)

  xform = output_entry.transform
  xform.handle = handle
  xform.time_constant = ad_prog.board.time_constant
  xform.legno_ampl_scale = cfg.scf(port)
  xform.legno_time_scale = ad_prog.tau
  output_entry.transform = xform

  runtime = dssim.sim_time/(xform.time_constant*xform.legno_time_scale)
  output_entry.runtime = runtime



def analyze(entry,ad_prog):
  update_experiment_params(ad_prog,entry)
  for output in list(entry.outputs()):
    update_output_params(ad_prog, output)

