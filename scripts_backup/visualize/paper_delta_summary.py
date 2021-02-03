import hwlib.model as modellib
import numpy as np
import util.util as util
import scripts.visualize.common as common
import matplotlib.pyplot as plt

def get_parameters(models):
  first_model = list(models.values())[0]
  params = {}
  params['enabled'] = 1  \
                      if all(map(lambda m: m.enabled, models.values())) \
                         else 0

  if first_model.block == "tile_in" or \
     first_model.block == "tile_out" or \
     first_model.block == "chip_in" or \
     first_model.block == "chip_out" or \
     first_model.block == "lut" or \
     first_model.block == "ext_chip_analog_in" or \
     first_model.block == "ext_chip_in" or \
     first_model.block == "ext_chip_out":
    model = models[("out",None)]
    params['alpha'] = model.gain
    params['beta'] = model.bias


  elif first_model.block == "tile_dac" or \
       first_model.block == "tile_adc":
    model = models[("out",None)]
    params['alpha'] = model.gain
    params['beta'] = model.bias

  elif first_model.block == "fanout":
    alphas = []
    betas = []
    for port in ["out0","out1","out2"]:
      model = models[(port,None)]
      alphas.append(model.gain)
      betas.append(model.bias)

    params = {}
    params['alpha'] = np.median(alphas)
    params['beta'] = np.median(betas)

  elif first_model.block == "multiplier" and \
       first_model.comp_mode == "vga":
    coeff_model = models[("coeff",None)]
    out_model = models[("out",None)]
    params = {}
    params['alpha'] = out_model.gain
    params['gamma'] = coeff_model.bias
    params['beta'] = out_model.bias
    params['error'] = out_model.bias_uncertainty.average

  elif first_model.block == "multiplier" and \
       first_model.comp_mode == "mul":
    model = models[("out",None)]
    params['alpha'] = model.gain
    params['beta'] = model.bias
    params['error'] = model.bias_uncertainty.average

  elif first_model.block == "integrator":
    ic_model = models[("out",":z[0]")]
    tc_model = models[("out",":z'")]
    params = {}
    params['alpha'] = ic_model.gain
    params['beta'] = ic_model.bias
    params['gamma'] = tc_model.gain
    params['error'] = ic_model.bias_uncertainty.average
  else:
    for model in models.values():
      print(model)
    raise Exception("unimpl")

  return params


def make_dist(block_name,blocks):
  params = {}
  for loc,data in blocks.items():
    paramset = get_parameters(data)
    for p,v in paramset.items():
      if not p in params:
        params[p] = []
      params[p].append(v)

  n = len(list(params.values())[0])
  print("-- %s [%d] --" % (block_name,n))
  dist = {}
  for p,v in params.items():
    if p == "enabled":
      print("%s %d/%d" % (p,sum(v),len(v)))
    else:
      print("-> %s" % p)
      dist[p] = (np.mean(v),np.std(v))
      #plt.hist(v, normed=True, bins=30)
      #plt.ylabel('Probability');
      #plt.savefig("%s.png" % (p))
      #print("mean=%f" % (np.mean(v)))
      #print("median=%f" % (np.median(v)))
      #print("std=%f" % (np.std(v)))
      #plt.clf()
      #input()

  return dist

def get_mode(model):
  if model.block == "tile_in" or \
     model.block == "tile_out" or \
     model.block == "chip_in" or \
     model.block == "chip_out" or \
     model.block == "lut" or \
     model.block == "ext_chip_analog_in" or \
     model.block == "ext_chip_in" or \
     model.block == "ext_chip_out":
    return ''

  elif model.block == "multiplier":
    if model.comp_mode == "vga":
      scale_mode = "%s%s" % (model.scale_mode[0][0],
                             model.scale_mode[1][0])
    else:
      scale_mode = "%s%s%s" % (model.scale_mode[0][0],
                               model.scale_mode[1][0],
                               model.scale_mode[2][0])
    return "%s/%s" % (model.comp_mode, scale_mode)

  elif model.block == "fanout" or \
       model.block == "tile_adc":
    return model.scale_mode[0]

  elif model.block == "tile_dac":
    return model.scale_mode[1][0]

  elif model.block == "integrator":
    return "%s%s" % (model.scale_mode[0][0],
                     model.scale_mode[1][0])

  else:
    print(model)
    input("unimpl")
    raise Exception("unimplemented")
def get_table(obj_tag,obj):
  db = modellib.ModelDB(calib_obj=obj)
  by_ident = {}
  by_block = {}
  for model in db.get_all():
    ident = "%s-%s-%s" % (model.block, \
                          "comp-mode" \
                          if model.block == "fanout" \
                          else model.comp_mode, \
                          model.scale_mode)

    if not ident in by_ident:
      by_ident[ident] = {}
    if not model.block in by_block:
      by_block[model.block] = []
    if not model.loc in by_ident[ident]:
      by_ident[ident][model.loc] = {}

    by_ident[ident][model.loc][(model.port,model.handle)] = model
    if not ident in by_block[model.block]:
      by_block[model.block].append(ident)

  print("build table")
  desc = "delta model summary"
  table = common.Table('Delta Model Summary for %s' % obj_tag, \
                       desc, 'delta-%s' % obj_tag,'|c|cc|cccc|', \
                       benchmarks=False)
  fields = [
    'block',
    'mode',
    'alpha',
    'gamma',
    'beta',
    'error'
  ]
  table.set_fields(fields)
  table.horiz_rule()
  table.header()
  table.horiz_rule()

  for block,idents in by_block.items():
    if block == "tile_in" or \
       block == "tile_out" or \
       block == "chip_in" or \
       block == "lut" or \
       block == "chip_out" or \
       block == "ext_chip_out" or \
       block == "ext_chip_in" or \
       block == "ext_chip_analog_in":
      continue

    block_name = block.replace("_","\_")
    for idx,ident in enumerate(idents):
      model = list(list(by_ident[ident].values())[0].values())[0]
      dists = make_dist(ident,by_ident[ident])
      row = {}
      if idx == 0:
        row['block'] = block_name
      else:
        row['block'] = ''

      row['mode'] = get_mode(model)
      if "alpha" in dists:
        m,s = dists['alpha']
        row['alpha'] = "$%.2f \pm %.2f$" % (m,s)
      else:
        row['alpha'] = ''

      if "beta" in dists:
        m,s = dists['beta']
        row['beta'] = "$%.2f \pm %.2f$" % (m,s)
      else:
        row['beta'] = ''

      if "gamma" in dists:
        m,s = dists['gamma']
        row['gamma'] = "$%.2f \pm %.2f$" % (m,s)
      else:
        row['gamma'] = ''

      if "error" in dists:
        m,s = dists['error']
        row['error'] = "$%.3f \pm %.2f$" % (m,s)
      else:
        row['error'] = ''


      table.data(None,row)

  table.horiz_rule()
  table.write(common.get_path('delta-models-%s.tbl' % obj.value))

def visualize(arg=None):
  db = modellib.ModelDB()
  get_table("maxfit",util.CalibrateObjective.MAX_FIT)
  get_table("minerr",util.CalibrateObjective.MIN_ERROR)
