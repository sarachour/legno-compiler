import hwlib.hcdc.llenums as llenums
import phys_model.phys_util as phys_util
import ops.interval as ivallib
import itertools
import numpy as np
import matplotlib.pyplot as plt

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
    patches = list(phys_util.split_interval(bounds, \
                                            self.num_patches))
    self._patches[var] = patches

  def ticks(self,var):
    bnds = self._patches[var]
    return list(map(lambda bnd: \
                    round((bnd.upper+bnd.lower)/2.0,2), \
      self._patches[var]))

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
      sub_output = phys_util.get_subarray(output,indices)
      sub_inputs = {}
      for v in variables:
        sub_inputs[v] = phys_util.get_subarray(inputs[v], \
                                               indices)
      yield patch,sub_inputs,sub_output




def heatmap(physblk,output_file,inputs,output,n,amplitude=None):
  bounds = physblk.get_bounds()
  surf = ParametricSurface(n)
  for var in inputs.keys():
    surf.add_variable(var,ivallib.Interval(bounds[var][0], \
                                           bounds[var][1]))

  assert(len(surf.variables) <= 2)
  if len(surf.variables) == 2:
    data = np.zeros((surf.num_patches,surf.num_patches));
    variables = list(surf.variables)
    v1 = surf.variables[0]
    v2 = surf.variables[1] if len(surf.variables) == 2 else None

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
      im = ax.imshow(data)
    else:
      im = ax.imshow(data,vmin=-amplitude,vmax=amplitude)

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("value", rotation=-90, va="bottom")
    fig.tight_layout()
    plt.savefig(output_file)
    plt.close()
  else:
    raise Exception("unimplemented")

def deviation(blk,output_file, \
              operation=llenums.ProfileOpType.INPUT_OUTPUT, \
              baseline=ReferenceType.MODEL_PREDICTION, \
              num_bins=10,
              amplitude=None,
              relative=False):
  data = blk.dataset.get_data(llenums.ProfileStatus.SUCCESS, \
                              operation)

  if baseline == ReferenceType.MODEL_PREDICTION:
    ref = blk.model.predict(data['inputs'])
  elif baseline == ReferenceType.CORRECTABLE_MODEL_PREDICTION:
    ref = blk.model.predict(data['inputs'], \
                            correctable_only=True)
  else:
    raise Exception("unimplemented")

  errors = []
  ampl = max(np.abs(ref)) if relative else 1.0
  for pred,meas in zip(ref, data['meas_mean']):
    errors.append((meas-pred)/ampl)

  heatmap(blk,output_file,data['inputs'],errors,n=10, \
          amplitude=amplitude)
