import ops.interval as ivallib
import util.util as util
import numpy as np
import itertools
import scipy.interpolate
import math

class ParametricSurface:

  def __init__(self):
    self._bounds= {}
    self.variables =[]

  @property
  def dim(self):
      return len(self.variables)

  def add_variable(self,var,bounds):
    assert(isinstance(bounds,ivallib.Interval))
    self._bounds[var] = bounds
    self.variables.append(var)

  def zero(self):
    self.outputs = [0.0]*len(self.outputs)


  def get(self,inputs):
    output = 0.0
    weight = 0.0
    # interpolation technique: inverse distance weighting
    expo = 4
    for idx,out in enumerate(self.outputs):
      dist = 0.0
      for v in inputs.keys():
        if v in self.inputs:
          dist += (self.inputs[v][idx] - inputs[v])**2

      dist = math.sqrt(dist)**expo
      if dist == 0:
        return out

      output += out*dist
      weight += dist

    return output/weight

  def get_grid(self,npts):
    grid = np.zeros(shape=tuple([npts]*self.dim))
    indices = list(map(lambda _: list(range(npts)), \
                       range(self.dim)))
    axes = {}
    for var in self.variables:
      ival = self._bounds[var]
      axes[var] = np.linspace(ival.lower,ival.upper,npts)

    for inds in itertools.product(*indices):
      vdict = {}
      for idx,var in zip(inds,self.variables):
        vdict[var] = self._bounds[var].by_index(idx,npts)

      grid[inds] = self.get(vdict)

    return axes,grid


  def fit(self,inputs,outputs,npts=10):
    self.inputs = inputs
    self.outputs = outputs

def build_surface_for_expr(block,cfg,rel,dataset,output,npts=10,normalize=1.0):
    surf = ParametricSurface()

    rel_vars = rel.vars()

    for inp_port in dataset.inputs.keys():
      if inp_port in rel_vars:
        port = block.inputs[inp_port]
        ival = port.interval[cfg.mode]
        surf.add_variable(inp_port,ival)

    for datum in dataset.data.keys():
      if datum in rel_vars:
        data_field = block.data[datum]
        ival = data_field.interval[cfg.mode]
        surf.add_variable(datum,ival)


    inputs = dataset.get_inputs()
    output = list(map(lambda o : o /normalize, output))
    #print("normalize: %s" % normalize)
    #print("output: [%f,%f]" % (min(output),max(output)))

    surf.fit(inputs,output)

    return surf

def build_surface(block,cfg,port,dataset,output,npts=10,normalize=1.0):
    surf = ParametricSurface()

    rel = block.outputs[port.name].relation[cfg.mode]
    return build_surface_for_expr(block,cfg,rel,dataset,output,npts,normalize)

