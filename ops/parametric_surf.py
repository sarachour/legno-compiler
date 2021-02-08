import ops.interval as ivallib
import util.util as util
import numpy as np
import itertools
import scipy.interpolate

class ParametricSurface:

  def __init__(self):
    self._bounds= {}
    self.variables =[]
    self.scale = 10

  @property
  def dim(self):
      return len(self.variables)

  def add_variable(self,var,bounds):
    assert(isinstance(bounds,ivallib.Interval))
    self._bounds[var] = bounds
    self.variables.append(var)

  def get(self,inputs):
    indices = [-1]*self.dim
    for idx,var in enumerate(self.variables):
      ival = self._bounds[var]
      indices[idx] = min(int(round(self.scale/ival.bound*inputs[var]) + self.scale), \
                         self.scale-1)

    idx = self.interp_inps[tuple(indices)]
    val = self.interp_out[idx.astype(int)]
    return float(val)

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
    def scale_val(a,ival):
      return int(round(a*self.scale/ival.bound))

    nvects = len(inputs[self.variables[0]])
    outputs = np.array(outputs)
    interpolants = np.zeros(shape=(nvects, self.dim))
    gridvals = np.zeros(shape=((self.scale*2)**self.dim, self.dim))
    self.interp_inps = np.zeros(shape=tuple([self.scale*2]*self.dim))


    print("mesh=%s" % str(gridvals.shape))
    mesh_inds = list(map(lambda _ : list(range(self.scale*2)), \
                               range(self.dim)))

    for k,indices in enumerate(itertools.product(*mesh_inds)):
      for idx,ind in enumerate(indices):
        gridvals[k,idx] = ind

      self.interp_inps[indices] = k

    for var_id,var in enumerate(self.variables):
      ival = self._bounds[var]
      ax = np.linspace(ival.lower,ival.upper,self.scale*2)
      for idx in range(self.scale*2):
        gridvals[idx,var_id] = scale_val(ax[idx],ival)

    print("interpolants=%s" % str(interpolants.shape))
    for var_id,var in enumerate(self.variables):
      ival = self._bounds[var]
      for idx in range(len(inputs[var])):
        interpolants[idx,var_id] = scale_val(inputs[var][idx],ival)

    ## unstructured data
    outputs_interp = scipy.interpolate.griddata(points=interpolants, \
                                                values=outputs,\
                                                xi=gridvals)
    self.interp_out = outputs_interp
    print("interp=%s" % str(self.interp_out.shape))


def build_surface(block,cfg,port,dataset,output,npts=10,normalize=1.0):
    surf = ParametricSurface()

    rel = block.outputs[port.name].relation[cfg.mode]
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


    inputs = {}
    for k,v in dataset.inputs.items():
      if k in rel_vars:
        inputs[k] = v
    for k,v in dataset.data.items():
      if k in rel_vars:
        inputs[k] = v

    output = list(map(lambda o : o /normalize, output))
    surf.fit(inputs,output)

    return surf
