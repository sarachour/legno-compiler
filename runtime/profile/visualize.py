import runtime.runtime_util as runtime_util

import hwlib.hcdc.llenums as llenums
import ops.interval as ivallib
import ops.parametric_surf as parsurflib

import itertools
import numpy as np
import matplotlib.pyplot as plt
import util.util as util

class ReferenceType:
  MODEL_PREDICTION = "model_pred"
  CORRECTABLE_MODEL_PREDICTION = "corr_model_pred"
  REFERENCE = "ref"


def get_maximum_value(physblk):
  bounds = physblk.get_bounds()
  output_ival = ivallib.Interval(bounds[physblk.output.name][0], \
                                  bounds[physblk.output.name][1])
  return output_ival.bound

def heatmap(physblk,output_file,dataset,output,n,relative=False, \
            amplitude=None):
  bounds = physblk.get_bounds()

  normalize_out = 1.0
  if relative:
    normalize_out = get_maximum_value(physblk)/100.0

  colormap_name = "coolwarm"

  if len(output) == 0:
    return

  surf = parsurflib.build_surface(physblk.block, \
                                  physblk.config, \
                                  physblk.output, \
                                  dataset, \
                                  output, \
                                  npts=n, \
                                  normalize=amplitude if not amplitude is None else 1.0)
 
  if not (len(surf.variables) <= 2):
    raise Exception("expected 1 or 2 variables. Received %s inputs" \
                    % str(inputs.keys()))


  if len(surf.variables) == 2:
    data = np.zeros((surf.num_patches,surf.num_patches));
    variables = list(surf.variables)
    v1 = surf.variables[0]
    v2 = surf.variables[1]

    fig,ax = plt.subplots()
    ax.set_xlabel(v1)
    ax.set_ylabel(v2)
    ax.set_xticks(np.arange(surf.num_patches))
    ax.set_yticks(np.arange(surf.num_patches))
    ax.set_xticklabels(surf.ticks(v1))
    ax.set_yticklabels(surf.ticks(v2))
    if amplitude is None:
      amplitude = np.max(np.abs(util.remove_nans(data)))

    im = ax.imshow(surf.data, \
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

    for patch_id,value in enumerate(surf.data):
      data[0,patch_id] = value
      data[1,patch_id] = value

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


  heatmap(delta_model,output_file,dataset,errors,n=num_bins, \
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

