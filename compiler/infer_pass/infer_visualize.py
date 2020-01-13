import matplotlib.pyplot as plt
import compiler.infer_pass.infer_util as infer_util
import util.util as util
import numpy as np
from scipy.ndimage.filters import gaussian_filter
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import seaborn as sns
import scipy.interpolate
import faulthandler

DO_PLOTS = False

def norm(v,vmin,vmax):
  return (v-vmin)/(vmax-vmin)

def get_min_value(out,use_delta_model):
  return 0.0

def get_max_value(out,use_delta_model,adc=False):
  if any(map(lambda o: abs(o) > 5.0, out)) and not adc:
    return 20.0*0.5
  else:
    return 2.0*0.5

def xbound(pts):
  if max(pts) > 10.0:
    return -20.0,20.0
  elif max(pts) > 1.5:
    return -2,2
  else:
    return -1,1

def heatmap1d(in0,out,value,labels,use_delta_model,adc=False):
  # strictly monotonic increasing
  if len(in0) <= 3:
    return

  x,y,z = [],[],[]
  vmin = get_min_value(out,use_delta_model)
  vmax = get_max_value(out,use_delta_model,adc=adc)
  xmin,xmax = xbound(in0)

  plt.clf()
  style = plt.get_cmap("magma")
  n = len(in0)
  zs = []
  xs = []
  for i in range(n):
    zs.append(value[i])
    zs.append(value[i])
    zs.append(value[i])
    xs.append([in0[i],0.0])
    xs.append([in0[i],0.5])
    xs.append([in0[i],1.0])

  faulthandler.enable()
  grid_x, grid_y = np.mgrid[min(in0):max(in0):100j, \
                            0.0:1.0:20j]

  grid_z = scipy.interpolate.griddata(points=xs, \
                                      values=zs, \
                                      xi=(grid_x,grid_y),
                                      method="linear")
  fig = plt.gca()
  # should be 8x wider than tall
  aspect = (xmax-xmin)/8.0
  plt.imshow(grid_z.T,
              extent=(min(in0),max(in0),0,1.0), \
              aspect=aspect, \
              origin='lower', \
              norm=Normalize(vmin,vmax), \
              cmap=style)
  plt.xlim(xmin,xmax)
  plt.ylim((0.0,1.0))
  #plt.axvline(linewidth=4, color='r')
  #plt.axis('off')
  #plt.xlabel(labels['in0'])
  #fig.axes.yaxis.set_ticklabels([])
  plt.colorbar(orientation='horizontal')

def heatmap2d(in0,in1,out,value,labels,use_delta_model):
  if len(in0) <= 3:
    return

  x,y,z = [],[],[]
  vmin = get_min_value(out,use_delta_model)
  vmax = get_max_value(out,use_delta_model)
  xmin,xmax = xbound(in0)
  ymin,ymax = xbound(in1)
  style = plt.get_cmap("magma")
  n = len(in0)
  xs = []
  for i in range(n):
    xs.append([in0[i],in1[i]])

  grid_x, grid_y = np.mgrid[min(in0):max(in0):100j, \
                            min(in1):max(in1):100j]

  grid_z = scipy.interpolate.griddata(points=xs, \
                                      values=value, \
                                      xi=(grid_x,grid_y),
                                      method="linear")
  aspect = (xmax-xmin)/(ymax-ymin)
  plt.imshow(grid_z.T,
              extent=(min(in0),max(in0), \
                      min(in1),max(in1)), \
              aspect=aspect,
              origin='lower', \
              norm=Normalize(vmin,vmax),
              cmap=style)

  plt.xlim(xmin,xmax)
  plt.ylim(ymin,ymax)
  plt.xlabel(labels['in0'])
  plt.ylabel(labels['in1'])
  plt.title(labels['out'])
  #plt.xlabel(labels['in0'])
  #fig.axes.yaxis.set_ticklabels([])
  plt.colorbar(orientation='horizontal')

'''
def make_block_identifier(model):
  loc = model.loc.replace("HDACv2,","")
  loc = loc.split("(")[1].split(")")[0]
  return "%s[%s]" % (model.block,loc)
'''

def save_figure(filename):
  plt.tight_layout()
  plt.savefig(filename,bbox_inches='tight')
  plt.clf()

def get_plot_parameters(model):
  IS_1D = {
    'fanout': True,
    'multiplier': False,
    'integrator': True,
    'tile_adc': True,
    'tile_dac': True
  }
  index = model.port.split('out')[1]
  LABELS = {
    'fanout': {'in0': 'Analog Input (uA)', \
               'out': 'Analog Output %s (uA)' % index},
    'tile_adc': {'in0': 'Analog Input (uA)', \
            'out': 'Digital Value (norm)'},
    'tile_dac': {'in0': 'Digital Value (norm)',
            'out': 'Analog Output (uA)'},
    'multiplier.vga': {'in0':'Analog Input (uA)', \
                       'in1':'Digital Gain (norm)', \
                   'out': 'Analog Output (uA)'},
    'multiplier.mul': {'in0':'Analog Input 0 (uA)', \
                        'in1':'Analog Input 1 (uA)',
                        'out': 'Analog Output (uA)'},
    'integrator': {'in0': 'Digital Initial Condition (norm)',
                   'out': 'Analog Output (uA)'}
  }
  SCALES = {
    'fanout': {'in0': 2.0,'out':2.0},
    'tile_adc': {'in0': 2.0,'out':1.0/128.0},
    'tile_dac': {'in0':1.0,'out':2.0},
    'multiplier.vga': {'in0':2.0,'in1':1.0,'out':2.0},
    'multiplier.mul': {'in0':2.0,'in1':2.0,'out':2.0},
    'integrator': {'in0':1.0, 'out':2.0}
  }
  is_1d = IS_1D[model.block]
  if model.block != 'multiplier':
    key = model.block
  else:
    key = "%s.%s" % (model.block,model.comp_mode)
  scales = SCALES[key]
  labels = LABELS[key]
  return is_1d,scales,labels

def plot_error(model,filename,dataset,use_delta_model=False,adc=False):
  if not DO_PLOTS:
    return

  is_1d,scales,labels = get_plot_parameters(model)
  if use_delta_model:
    tag = "with Delta Model"
  else:
    tag = ""


  def compute_error(meas,pred):
    if pred < 0:
      return abs(pred-meas)
    else:
      return abs(meas-pred)

  title = "|Error| of %s %s" % (labels['out'],tag)
  #plt.title(title)
  in0 = util.array_map(map(lambda x: x*scales['in0'], dataset.in0))
  if hasattr(model,'gain_offset'):
    inds = filter(lambda i: dataset.out[i] != 0.0, range(0,dataset.n))
    coeff = np.mean(np.array(list(map(lambda i: dataset.out[i]/(dataset.in0[i]*dataset.in1[i]), inds))))

    pred = infer_util.apply_model_vga(model,dataset.in0,dataset.in1, \
                                      dataset.out,coeff)
  else:
    pred = infer_util.apply_model(model,dataset.out)

  out,meas = dataset.out,dataset.meas
  if use_delta_model:
    err = util.array_map(map(lambda i: scales['out']*compute_error(meas[i],pred[i]), \
                                 range(dataset.n)))
  else:
    err = util.array_map(map(lambda i: scales['out']*compute_error(meas[i],out[i]), \
                                   range(dataset.n)))

  if is_1d:
    heatmap1d(in0,out,err,labels,use_delta_model,adc=adc)
  else:
    in1 = util.array_map(map(lambda x: x*scales['in1'], dataset.in1))
    heatmap2d(in0,in1,out,err,labels,use_delta_model)

  save_figure(filename)


def get_plot_name(model,tag):
    direc = infer_util.get_directory(model)
    if not model.handle is None:
      filename = "%s-%s-%s.png" \
                % (model.port,model.handle,tag)
    else:
      filename = "%s-%s.png" \
                % (model.port,tag)

    return "%s/%s" % (direc,filename)

