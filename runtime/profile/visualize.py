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



def remove_nans(arr):
  nparr = np.array(arr)
  return nparr[:,~np.isnan(nparr).any(axis=0)]

def get_maximum_value(physblk):
  bounds = physblk.get_bounds()
  output_ival = ivallib.Interval(bounds[physblk.output.name][0], \
                                  bounds[physblk.output.name][1])
  return output_ival.bound

def heatmap(physblk,output_file,inputs,output,n,relative=False, \
            amplitude=None):
  bounds = physblk.get_bounds()

  normalize_out = 1.0
  if relative:
    normalize_out = get_maximum_value(physblk)/100.0

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
      value = np.mean(remove_nans(out))
      data[patch[v1],patch[v2]] = value/normalize_out
      assert(value != np.nan)

    fig,ax = plt.subplots()
    ax.set_xlabel(v1)
    ax.set_ylabel(v2)
    ax.set_xticks(np.arange(surf.num_patches))
    ax.set_yticks(np.arange(surf.num_patches))
    ax.set_xticklabels(surf.ticks(v1))
    ax.set_yticklabels(surf.ticks(v2))
    if amplitude is None:
      amplitude = np.max(np.abs(remove_nans(data)))

    im = ax.imshow(data, \
                    cmap=plt.get_cmap(colormap_name), \
                    vmin=-amplitude, \
                    vmax=amplitude)


    cbar = ax.figure.colorbar(im, ax=ax)
    hm_label = "error (%)" if relative else "error (uA)"
    cbar.ax.set_ylabel(hm_label, rotation=-90, va="bottom")
    fig.tight_layout()
    plt.savefig(output_file)
    plt.close()

  elif len(surf.variables) == 1:
    v1 = surf.variables[0]
    data = np.zeros((2,surf.num_patches));

    for patch,inps,out in surf.divide(inputs,output):
      data[0,patch[v1]] = np.mean(out)/normalize_out
      data[1,patch[v1]] = np.mean(out)/normalize_out

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
    hm_label = "error (%)" if relative else "error (uA)"
    cbar.ax.set_ylabel(hm_label, rotation=-90, va="bottom")
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
    errors = delta_model.errors(dataset, \
                                init_cond=init_cond)
  elif baseline == ReferenceType.CORRECTABLE_MODEL_PREDICTION:
    errors = delta_model.errors(dataset, \
                              correctable_only=True, \
                              init_cond=init_cond)
  else:
    raise Exception("unimplemented")

  inps = {}
  for k,v in dataset.inputs.items():
    inps[k] = v
  for k,v in dataset.data.items():
    inps[k] = v

  if delta_model.block.name == "mult" \
     and str(delta_model.config.mode) == "(h,m,m)":
    print(delta_model)
    for idx in range(len(errors)):
      ix = dict(map(lambda v: (v,inps[v][idx]), inps.keys()))
      print("inps=%s meas=%f err=%f" % (ix,dataset.meas_mean[idx],errors[idx]))
    print("max-val=%s" % get_maximum_value(delta_model))
    input("continue")

  heatmap(delta_model,output_file,inps,errors,n=num_bins, \
          amplitude=amplitude, \
          relative=relative)

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



def model_error_histogram(delta_models,png_file,num_bins=10,relative=False):
  if len(delta_models) < 3:
    return

  normalize_out = 1.0
  if relative:
    limit = max(map(lambda physblk: get_maximum_value(physblk), delta_models))
    normalize_out = limit/100.0



  fig, axs = plt.subplots(1, 1, tight_layout=True)
  model_errors = list(filter(lambda err: err < 20, \
                             map(lambda dm: dm.model_error / normalize_out, \
                                 delta_models)))

  axs.hist(model_errors, bins=num_bins)

  hm_label = "error (%)" if relative else "error (uA)"
  axs.set_xlabel(hm_label)

  # We can set the number of bins with the `bins` kwarg
  fig.tight_layout()
  plt.savefig(png_file)
  plt.close()


def objective_fun_histogram(delta_models,png_file,num_bins=10):
  if len(delta_models) < 3:
    return

  fig, axs = plt.subplots(1, 1, tight_layout=True)
  objvals = []
  for model in delta_models:
    try:
      objval = model.spec.objective.compute(model.variables())
      objvals.append(objval)
    except Exception as e:
      continue

  axs.hist(objvals, bins=num_bins)
  fig.tight_layout()
  plt.savefig(png_file)
  plt.close()

