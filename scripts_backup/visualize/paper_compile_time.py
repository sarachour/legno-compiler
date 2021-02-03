import util.paths as pathlib
import os
import numpy as np
import scripts.visualize.common as common

def read_compile_times(subset):
  summary = {}

  for bmark in common.BenchmarkVisualization.benchmarks():
    ph = pathlib.PathHandler(subset,bmark,make_dirs=False)
    time_dir = ph.TIME_DIR
    for dirname, subdirlist, filelist in os.walk(time_dir):
      for fname in filelist:
        if not fname.endswith('.txt'):
          continue

        fpath = "%s/%s" % (dirname,fname)
        with open(fpath,'r') as fh:
          lines = fh.read().split("\n")
          comp_pass = lines[0]
          nonempty_lines = filter(lambda l: l != "", lines[1:])
          times = np.array(list(map(lambda l: float(l), \
                                    nonempty_lines)))
          if not bmark in summary:
            summary[bmark] = {}

          if len(times) == 0:
            summary[bmark][comp_pass] = (None,0.0)
          else:
            avg_time = np.mean(times)
            std_time = np.std(times)
            summary[bmark][comp_pass] = (avg_time,std_time)

  return summary

def to_runtime_table(summary):
  def format_runtime(r):
    mean,std = r
    if mean is None:
      return "n/a"

    if not std == 0.0:
      return "%.2f $\pm$ %.2f s" % (mean,std)
    else:
      return "%.2f s $\pm$ %.2f" % (mean,std)

  desc = "compilation time, broken down by compilation pass"
  table = common.Table('Compilation Times', \
                       desc, 'comptime','|c|ccc|')
  table.set_fields(['lgraph','lscale','srcgen'])
  table.horiz_rule()
  table.header()
  table.horiz_rule()
  for bmark in table.benchmarks():
    if not bmark in summary:
      continue

    row = {}
    if not 'lgraph' in summary[bmark]:
      row['lgraph'] = '-'
    else:
      row['lgraph'] = format_runtime(summary[bmark]['lgraph'])

    if not 'lscale' in summary[bmark]:
      row['lscale'] = '-'
    else:
      row['lscale'] = format_runtime(summary[bmark]['lscale'])

    if not 'srcgen' in summary[bmark]:
      row['srcgen'] = '-'
    else:
      row['srcgen'] = format_runtime(summary[bmark]['srcgen'])

    table.data(bmark,row)

  table.horiz_rule()
  table.write(common.get_path('compile-time.tbl'))


def visualize(db):
  summary = read_compile_times('extended')
  to_runtime_table(summary)
