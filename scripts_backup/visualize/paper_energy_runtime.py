import scripts.visualize.common as common
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import math
import util.util as util

def visualize(db):
  data = common.get_data(db,series_type='program',executed_only=False)
  desc = "performance, energy and quality for HDACv2 Board"
  table = common.Table("Results", desc, "tbl:performance", \
                       layout = "|c|c|cc|")
  table.two_column = False
  header = [
          'runtime', \
          'power', \
          'energy'
  ]
  table.set_fields(header)
  table.horiz_rule();
  table.header()
  table.horiz_rule();
  for ser in common.Plot.benchmarks():
    if data.has_series(ser):
      fields = ['runtime','energy','model']
      result = data.get_data(ser,fields)
      runtime,power,model = result

      row = {}
      n = len(runtime)
      mu,sig = np.mean(runtime),np.std(runtime)
      row['runtime'] = "%.2f $\pm$ %.2f ms" % (mu*1e3,sig*1e3)
      mu,sig = np.mean(power),np.std(power)
      row['power'] = "%.2f $\pm$ %.2f $\mu$W" % (mu*1e6,sig*1e6)
      energy = list(map(lambda i: runtime[i]*power[i], range(n)))
      mu,sig = np.mean(energy),np.std(energy)
      row['energy'] = "%.2f $\pm$ %.2f $\mu$J" % (mu*1e6,sig*1e6)
      pars = util.unpack_model(model[0])
      row['bandwidth'] = "%dkhz" % int(pars['bandwidth_khz'])

      table.data(ser,row)
  table.horiz_rule();
  table.write(common.get_path('energy-runtime.tbl'))
