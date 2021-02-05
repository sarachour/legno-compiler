import ops.interval as ivallib
import util.util as util
import numpy as np
import itertools
import scipy.interpolate

class ParametricSurface:

  def __init__(self,num_patches=3):
    self._patches = {}
    self.num_patches = num_patches
    self.variables =[]
    self.data = None

  @property
  def dim(self):
      return len(self.variables)

  def add_variable(self,var,bounds):
    assert(isinstance(bounds,ivallib.Interval))
    patches = list(ivallib.split_interval(bounds, \
                                            self.num_patches))
    self._patches[var] = patches
    self.variables.append(var)

  def patch_to_intervals(self,patch):
      ivals = {}
      for var, patch_id in patch.items():
          ivals[var] = self._patches[var][patch_id]

      return ivals

  def ticks(self,var):
    bnds = self._patches[var]
    return list(map(lambda bnd: \
                    round((bnd.upper+bnd.lower)/2.0,2), \
      self._patches[var]))

  def get(self,point):
    patches = [-1]*self.dim
    for v in self.variables:
        if not v in point:
            raise Exception("missing variable <%s>" % v)

    for varname in self.variables:
        idx = self.variables.index(varname)
        val = point[varname]
        for patch_id, patch in enumerate(self._patches[varname]):
            if patch.contains_value(val):
                patches[idx] = patch_id


        assert(patches[idx] >= 0)

    value = self.data[tuple(patches)]
    return float(value)


  def interpolate(self,patch,inputs,outputs):
    n_pts = len(outputs)
    input_data = np.zeros((n_pts,len(self.variables)));
    ivals = self.patch_to_intervals(patch)
    pt = list(map(lambda v: ivals[v].middle,self.variables))

    for idx in range(n_pts):
      for varid,v in enumerate(self.variables):
        input_data[idx,varid] = inputs[v][idx]

    output_data = np.array(outputs)
    print('-- vars --')
    print(self.variables)
    print('-- input --')
    print(input_data)
    print('-- output --')
    print(output_data)
    print('-------')
    ys = scipy.interpolate.griddata(input_data, \
                                    output_data, \
                                    [pt])
    return ys[0]

  def divide(self,inputs,output):
    def test_index(patch,index):
      for var,patch_id in patch.items():
        var_range = self._patches[var][patch_id]
        value = inputs[var][index]
        if not var_range.contains_value(value):
          return False
      return True

    n = len(output)
    patches = list(range(0,self.num_patches))
    variables = list(self.variables)
    combos = [patches]*len(variables)
    for combo in itertools.product(*combos):
      patch = dict(zip(variables,combo))
      indices = list(filter(lambda i : test_index(patch,i), \
                       range(0,n)))
      sub_output = util.get_subarray(output,indices)
      sub_inputs = {}
      for v in variables:
        sub_inputs[v] = util.get_subarray(inputs[v], \
                                               indices)
      if len(sub_output) == 0:
        sub_inputs = {}
        for v in variables:
          sub_inputs[v] = [patch[v]]
        sub_output = self.interpolate(patch,inputs,output)
        yield patch,sub_inputs,[sub_output]
      else:
        yield patch,sub_inputs,sub_output



def build_surface(block,cfg,port,dataset,output,npts=10,normalize=1.0):
    surf = ParametricSurface(npts)

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


    dim = len(inputs.keys())
    array_shape = tuple([surf.num_patches]*dim)
    surf.data = np.zeros(array_shape);

    for patch,inps,out in surf.divide(inputs,output):
      value = np.mean(util.remove_nans(out))
      index = list(map(lambda v: patch[v], surf.variables))
      surf.data[index] = value/normalize
      assert(value != np.nan)

    return surf

