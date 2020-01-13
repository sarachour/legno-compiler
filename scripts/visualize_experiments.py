import scripts.visualize.paper_energy_runtime  \
  as paper_energy_runtime
import scripts.visualize.paper_quality_energy_runtime  \
  as paper_quality_energy_runtime
import scripts.visualize.paper_energy_runtime  \
  as paper_energy_runtime
import scripts.visualize.paper_bmark_summary as paper_bmark_summary
import scripts.visualize.paper_circuit_summary as paper_circuit_summary
import scripts.visualize.paper_chip_summary as paper_chip_summary
import scripts.visualize.paper_compile_time as paper_compile_time
import scripts.visualize.paper_quality_graphs as paper_quality_graphs
import scripts.visualize.paper_delta_summary as paper_delta_summary
import matplotlib.pyplot as plt
import numpy as np
import math
from scripts.expdriver_db import ExpDriverDB


def execute(args):
  name = args.type
  opts = {
    'paper-energy-runtime': \
    paper_energy_runtime.visualize,
    'paper-quality-energy-runtime': \
    paper_quality_energy_runtime.visualize,
    'paper-energy-runtime': \
    paper_energy_runtime.visualize,
    'paper-chip-summary': paper_chip_summary.visualize,
    'paper-benchmark-summary': paper_bmark_summary.visualize,
    'paper-circuit-summary': paper_circuit_summary.visualize,
    'paper-compile-time': paper_compile_time.visualize,
    'paper-quality-graphs': paper_quality_graphs.visualize,
    'paper-delta-summary': paper_delta_summary.visualize,

  }
  if name in opts:
    try:
      db = ExpDriverDB()
      opts[name](db)
    except Exception as e:
      print("could not load database.")
      opts[name](None)

  else:
    for opt in opts.keys():
      print(": %s" % opt)
    raise Exception("unknown routine <%s>" % name)
