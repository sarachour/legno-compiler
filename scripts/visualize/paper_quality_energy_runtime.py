import scripts.visualize.common as common
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import math
import util.util as util

def visualize(db):
  data = common.get_data(db,series_type='program',subset='extended')
  desc = "performance, energy and quality for HDACv2 Board"
  table = common.Table("Results", desc, "tbl:performance", \
                       layout = "|c|c|ccc|")
  table.two_column = False
  header = [
          'runtime', \
          'power', \
          'energy', \
          '% rmse' \
  ]
  table.set_fields(header)
  table.horiz_rule();
  table.header()
  table.horiz_rule();
  for ser in common.Plot.benchmarks():
    print(ser)
    if data.has_series(ser):
      fields = ['runtime','energy','quality','quality_variance','model']
      result = data.get_data(ser,fields)
      runtime,energy,quality,quality_variance,model = result
      idx = np.argmin(quality)

      row = {}
      pars = util.unpack_model(model[idx])
      row['runtime'] = "%.2f ms" % (runtime[idx]*1e3)
      row['power'] = "%.2f $\mu$W" % (energy[idx]*1e6)
      row['energy'] = "%.2f $\mu$J" % (energy[idx]*runtime[idx]*1e6)
      row['% rmse'] = "%.2f" % quality[idx]
      #row['% rmse'] = "%.4f $\pm$ %.4f" \
      #                 % (np.mean(quality),np.std(quality))
      #row['minimum digital snr'] = "%f" % dig_error
      #row['minimum analog snr'] = "%f" % ana_error
      row['bandwidth'] = "%dkhz" % int(pars['bandwidth_khz'])

      table.data(ser,row)
  table.horiz_rule();
  table.write(common.get_path('quality-energy-runtime.tbl'))
