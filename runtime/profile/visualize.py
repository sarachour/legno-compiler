import runtime.runtime_util as runtime_util

import hwlib.hcdc.llenums as llenums
import ops.interval as ivallib

import itertools
import numpy as np
import matplotlib.pyplot as plt
import scipy.interpolate

class ReferenceType:
  MODEL_PREDICTION = "model_pred"
  CORRECTABLE_MODEL_PREDICTION = "corr_model_pred"
  REFERENCE = "ref"

class ParametricSurface:

  def __init__(self,num_patches=3):
    self._patches = {}
    self.num_patches = num_patches

  @property
  def variables(self):
    return list(self._patches.keys())

  def add_variable(self,var,bounds):
    assert(isinstance(bounds,ivallib.Interval))
    patches = list(runtime_util.split_interval(bounds, \
                                            self.num_patches))
    self._patches[var] = patches

  def ticks(self,var):
    bnds = self._patches[var]
    return list(map(lambda bnd: \
                    round((bnd.upper+bnd.lower)/2.0,2), \
      self._patches[var]))

  def interpolate(self,patch,inputs,outputs):
    n_pts = len(outputs)
    input_data = np.zeros((n_pts,len(self.variables)));
    pt = [0]*len(self.variables)
    for varid,v in enumerate(self.variables):
      patch_id = patch[v]
      var_range = self._patches[v][patch_id]
      pt[varid] = var_range.middle

    for idx in range(n_pts):
      for varid,v in enumerate(self.variables):
        input_data[idx,varid] = inputs[v][idx]

    output_data = np.array(outputs)
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
      sub_output = runtime_util.get_subarray(output,indices)
      sub_inputs = {}
      for v in variables:
        sub_inputs[v] = runtime_util.get_subarray(inputs[v], \
                                               indices)
      if len(sub_output) == 0:
        sub_inputs = {}
        for v in variables:
          sub_inputs[v] = [patch[v]]
        sub_output = self.interpolate(patch,inputs,output)
        yield patch,sub_inputs,[sub_output]
      else:
        yield patch,sub_inputs,sub_output




def heatmap(physblk,output_file,inputs,output,n,amplitude=None):
  bounds = physblk.get_bounds()
  surf = ParametricSurface(n)
  colormap_name = "coolwarm"
  if len(output) == 0:
    return

  for var in inputs.keys():
    ival = ivallib.Interval(bounds[var][0], \
                            bounds[var][1])
    # there is some variation
    dynamic_range = max(inputs[var]) - min(inputs[var])
    if dynamic_range > 1e-5:
      surf.add_variable(var,ival)

  if not (len(surf.variables) <= 2):
    raise Exception("expected 1 or 2 variables. Received %s inputs" \
                    % str(inputs.keys()))
  if len(surf.variables) == 2:
    data = np.zeros((surf.num_patches,surf.num_patches));
    variables = list(surf.variables)
    v1 = surf.variables[0]
    v2 = surf.variables[1]
    for patch,inps,out in surf.divide(inputs,output):
      data[patch[v1],patch[v2]] = np.mean(out)

    fig,ax = plt.subplots()
    ax.set_xlabel(v1)
    ax.set_ylabel(v2)
    ax.set_xticks(np.arange(surf.num_patches))
    ax.set_yticks(np.arange(surf.num_patches))
    ax.set_xticklabels(surf.ticks(v1))
    ax.set_yticklabels(surf.ticks(v2))
    if amplitude is None:
      amplitude = np.max(np.abs(data))

    im = ax.imshow(data, \
                    cmap=plt.get_cmap(colormap_name), \
                    vmin=-amplitude, \
                    vmax=amplitude)


    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("value", rotation=-90, va="bottom")
    fig.tight_layout()
    plt.savefig(output_file)
    plt.close()

  elif len(surf.variables) == 1:
    v1 = surf.variables[0]
    data = np.zeros((2,surf.num_patches));
    for patch,inps,out in surf.divide(inputs,output):
      data[0,patch[v1]] = np.mean(out)
      data[1,patch[v1]] = np.mean(out)

    fig,ax = plt.subplots()
    ax.set_xlabel(v1)
    ax.set_xticks(np.arange(surf.num_patches))
    ax.set_xticklabels(surf.ticks(v1))
    if amplitude is None:
      amplitude = np.max(np.abs(data))

    im = ax.imshow(data, \
                    cmap=plt.get_cmap(colormap_name), \
                    vmin=-amplitude, \
                    vmax=amplitude)

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("value", rotation=-90, va="bottom")
    fig.tight_layout()
    plt.savefig(output_file)
    plt.close()


  else:
    raise Exception("unimplemented")

def deviation_(delta_model,dataset,output_file, \
               baseline=ReferenceType.MODEL_PREDICTION, \
               init_cond=False, \
               num_bins=10,
               amplitude=None,
               relative=False):

  if baseline == ReferenceType.MODEL_PREDICTION:
    ref = delta_model.predict(dataset, \
                              init_cond=init_cond)
  elif baseline == ReferenceType.CORRECTABLE_MODEL_PREDICTION:
    ref = delta_model.predict(dataset, \
                              correctable_only=True, \
                              init_cond=init_cond)
  else:
    raise Exception("unimplemented")

  #valid_vars = blk.model.delta_model.vars()
  #print("valid variables: %s" % valid_vars)
  #for idx in range(0,len(ref)):
  #  pred = ref[idx]
  #  inps = {}
  #  for var in dataset.inputs['inputs']:
  #    inps[var] = data['inputs'][var][idx]
  #  obs = data['meas_mean'][idx]
    #print("inputs=%s pred=%s obs=%s" % (inps,pred,obs))
    #input("continue")

  inps = {}
  for k,v in dataset.inputs.items():
    inps[k] = v
  for k,v in dataset.data.items():
    inps[k] = v

  errors = []
  ampl = max(np.abs(ref)) if relative and len(ref) > 0 else 1.0
  for pred,meas in zip(ref, dataset.meas_mean):
    errors.append((meas-pred)/ampl)

  heatmap(delta_model,output_file,inps,errors,n=num_bins, \
          amplitude=amplitude)

def deviation(delta_model,dataset,output_file, \
              baseline=ReferenceType.MODEL_PREDICTION, \
              num_bins=10,
              amplitude=None,
              relative=False):
  if delta_model.is_integration_op:
    deviation_(delta_model,dataset, \
               output_file, \
               init_cond=True, \
               num_bins=num_bins, \
               baseline=baseline, \
               amplitude=amplitude, \
               relative=relative)
  else:
    deviation_(delta_model,dataset, \
               output_file, \
               init_cond=False, \
               num_bins=num_bins, \
               baseline=baseline, \
               amplitude=amplitude, \
               relative=relative)


