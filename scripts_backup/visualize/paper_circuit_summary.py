import scripts.visualize.common as common
import numpy as np
import matplotlib.pyplot as plt
from hwlib.adp import AnalogDeviceProg
from enum import Enum
import util.util as util

def count_components(circ):
  summary = {'blocks': {}, 'total':0.0,'conns':0.0}
  for block_name,loc,_ in circ.instances():
    if not block_name in summary['blocks']:
      summary['blocks'][block_name] = 0
    summary['blocks'][block_name] += 1
    summary['total'] += 1

  summary['conns']= len(list(circ.conns()))
  return summary

def average_comp_count(circs):
  agg = {'blocks':{},'total':0.0,'conns':0.0}
  for c in circs:
    result = count_components(c)
    for blk,cnt in result['blocks'].items():
      if not blk in agg['blocks']:
        agg['blocks'][blk] = 0.0
      agg['blocks'][blk] += cnt

    agg['total'] += result['total']
    agg['conns'] += result['conns']


  n = len(circs)
  for blk in agg['blocks'].keys():
    agg['blocks'][blk] /= n

  agg['conns'] /= n
  agg['total'] /= n
  return agg

def to_lgraph_table(circuits):
  to_header = {
    'tile_out': 'route',
    'tile_in': 'route',
    'chip_out': 'route',
    'chip_in': 'route',
    'ext_chip_out': 'cout',
    'ext_chip_in': 'cin',
    'tile_dac':'dac',
    'tile_adc':'adc',
    'lut':'lut',
    'fanout': 'fan',
    'multiplier': 'mul',
    'integrator': 'int',
    'conns': 'connections'
  }
  desc = 'analog chip configuration statistics'
  table = common.Table('Circuit Configurations', \
                       desc, 'circ-lgraph','|c|c|ccccccccc|c|')
  fields = ['blocks','int','mul', \
                    'fan','adc','dac','lut', \
                    'cout', 'cin', \
                    'route','connections']
  table.set_fields(fields)
  table.horiz_rule()
  table.header()
  table.horiz_rule()
  for bmark in table.benchmarks():
    row = {}
    if not bmark in circuits:
      continue

    data = average_comp_count(circuits[bmark])
    for f in fields:
      row[f] = 0

    for key,value in data['blocks'].items():
      row[to_header[key]] += value

    row[to_header['conns']] += data['conns']
    row['blocks'] = data['total']
    for f,v in row.items():
      row[f] = "%d" % v

    table.data(bmark,row)

  table.horiz_rule()
  table.write(common.get_path('circuit-lgraph.tbl'))

def count_scaling_factors(circ,model):
  #conc_circ = ConcCirc.read(board,conc_circ)
  pars = util.unpack_model(model)
#model,dig_error,ana_error,bandwidth
  scvals = []
  injvals = []
  n_injvars = 0
  n_scvars = 0
  for block_name,loc,_ in circ.instances():
    cfg = circ.config(block_name,loc)
    for ivar,value in cfg.inject_vars():
      injvals.append(value)
      n_injvars += 1

    for svar,value in cfg.scale_vars():
      scvals.append(value)
      n_scvars += 1

  summary = {}
  summary['scvars'] = n_scvars
  summary['scvals'] = len(set(scvals))
  summary['injvars'] = n_injvars
  summary['injvals'] = len(set(injvals))
  summary['tau']=circ.tau
  summary['mdpe'] = pars['mdpe']
  summary['mape'] = pars['mape']
  summary['bandwidth'] = pars['bandwidth_khz']
  return summary


def average_scale_factor_count(circs,models):
  for c,m in zip(circs,models):
    summary = count_scaling_factors(c,m)
    return summary

def to_lscale_table(circuits,models):
  desc = "statistics for \lscale compilation pass"
  table = common.Table('Circuit Configurations', \
                       desc, 'circ-lscale','|c|ccc|ccc|cc|')

  hdr1 = [
    '','','','',
    '\multicolumn{3}{c|}{scale factors}',
    '\multicolumn{2}{c|}{injected vars}'
  ]
  hdr2 = [
    'benchmarks',
    'DQM','AQM','max freq','time',
    'total','unique',
    'total','unique',
  ]
  fields = [
    'mdpe',
    'mape',
    'max freq',
    'time constant',
    'scale vars',
    'unique scale vars',
    'free vars',
    'unique free vars'

  ]
  table.set_fields(fields)
  table.horiz_rule()
  table.raw(hdr1);
  table.raw(hdr2);
  table.horiz_rule()

  for bmark in table.benchmarks():
    if not bmark in circuits:
      continue

    summary = average_scale_factor_count(circuits[bmark], \
                                         models[bmark])
    row = {}
    row['mdpe'] = "%.3f" % (summary['mdpe'])
    row['mape'] = "%.3f" % (summary['mape'])
    row['max freq'] = "%dk" % int(summary['bandwidth'])
    row['time constant'] = "%.2f" % summary['tau']
    row['scale vars'] = "%d" % summary['scvars']
    row['unique scale vars'] = "%d" % summary['scvals']
    row['free vars'] = "%d" % summary['injvars']
    row['unique free vars'] = "%d" % summary['injvals']
    table.data(bmark,row)

  table.horiz_rule()
  table.write(common.get_path('circuit-lscale.tbl'))

def visualize(db):
  data = common.get_data(db,series_type='identifier',executed_only=False)
  circuits = {}
  models = {}
  for ser in data.series():
    fields = ['adp','model','program','subset']
    lgraph_files,_models,progs,subsets = data.get_data(ser, fields)
    prog = progs[0]
    n = len(lgraph_files)
    valid_indices = list(filter(lambda i: subsets[i] == 'extended' and \
                           "n" in _models[i], \
                           range(n)))
    if len(valid_indices) == 0:
      continue

    circuits[prog] = list(map(lambda  i: AnalogDeviceProg.read(None, \
                                                                lgraph_files[i]), \
                               valid_indices))
    models[prog] = _models

  to_lgraph_table(circuits)
  to_lscale_table(circuits,models)
