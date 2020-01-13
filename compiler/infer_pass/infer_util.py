import numpy as np
import itertools
import util.util as util
import util.config as CFG
from hwlib.model import PortModel, ModelDB
import hwlib.hcdc.enums as spec_enums
import lab_bench.lib.chipcmd.data as chipcmd

CALIB_OBJ = util.CalibrateObjective.MIN_ERROR

def about_one(gain):
    return gain >= 0.990 and gain <= 1.01

def tightest_bounds(bnds):
    lb = min(map(lambda b: b[0] \
                 if not b[0] is None \
                 else 1e6, bnds))
    ub = min(map(lambda b: b[1] \
                 if not b[1] is None \
                 else 1e6, bnds))
    return (lb,ub)

def apply_model_vga(model,x0,x1,out,coeff):
    result = coeff*(model.gain*x1+model.gain_offset)*(x0) + model.bias
    return result

def apply_model(model,xdata):
    x = xdata
    result = (model.gain)*(x) + model.bias
    return result

# A[B[i]]
def indirect_index(data,inds):
  subdata = []
  subd = np.array(list(map(lambda i: data[i], inds)))
  return subd

def get_data_by_mode(dataset,mode):
    modes = dataset['mode']
    inds = list(filter(lambda i: modes[i] == mode, range(len(modes))))
    bias = indirect_index(dataset['bias'],inds)
    noise = indirect_index(dataset['noise'],inds)
    in0 = indirect_index(dataset['in0'],inds)
    in1 = indirect_index(dataset['in1'],inds)
    out = indirect_index(dataset['out'],inds)
    return bias,noise,in0,in1,out

def to_bool(value):
  return chipcmd.BoolType(value).boolean()

def to_sign(name):
  return chipcmd.SignType(name)

def to_loc(obj):
    chip = obj['chip']
    tile = obj['tile']
    slce = obj['slice']
    index = obj['index']
    loc = "(HDACv2,%d,%d,%d,%d)" \
          % (chip,tile,slce,index)
    return loc

def to_range(name):
  return spec_enums.RangeType(name)

def to_safe_loc(loc):
  loc = loc.replace("HDACv2,","")
  loc = loc.split("(")[1].split(")")[0]
  loc = "x".join(loc.split(","))
  return loc

def get_directory(model):
    def to_tag(mode):
        if isinstance(mode,tuple):
            tag = ''.join(map(lambda m: str(m)[0], mode))
        else:
            tag = str(mode)
        return tag
    block,loc = model.block,model.loc
    loc = to_safe_loc(loc)
    cm,sm = to_tag(model.comp_mode),to_tag(model.scale_mode)
    direc = "{path}/{block}-{loc}/{comp_mode}-{scale_mode}/{calib_obj}"
    conc_dir = direc.format(path=CFG.MODEL_PATH,
                            block=block,
                            loc=loc,
                            comp_mode=cm,
                            scale_mode=sm,
                            calib_obj=CALIB_OBJ.value)
    util.mkdir_if_dne(conc_dir)
    return conc_dir

def normalize_bound(bnds,scm):
  lb,ub = bnds
  if not lb is None:
      nlb = lb*1.0/scm.coeff()
  else:
      nlb = 1.0

  if not ub is None:
      nub = ub*1.0/scm.coeff()
  else:
      nub = 1.0

  def clamp(v):
      return min(max(v,0.5),1.0)

  return [clamp(nlb),clamp(nub)]

