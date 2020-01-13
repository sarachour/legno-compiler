import compiler.infer_pass.infer_util as infer_util
import compiler.infer_pass.infer_visualize as infer_vis
import compiler.infer_pass.infer_fit as infer_fit
from scipy import stats
import numpy as np

from hwlib.model import PortModel

def build_config(meta):
  loc = infer_util.to_loc(meta['loc'])
  comp_mode=  "*"
  print(meta.keys())
  scale_mode = infer_util.to_range(meta['rng'])

  out = PortModel('tile_adc',loc,'out', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode, \
                  calib_obj=infer_util.CALIB_OBJ)

  inp = PortModel('tile_adc',loc,'in', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode, \
                  calib_obj=infer_util.CALIB_OBJ)

  return scale_mode,inp,out

def infer(obj):
  scm,model_in,model_out = build_config(obj['metadata'])

  out_bias,out_nz,_,_,out_vals = infer_util \
                              .get_data_by_mode(obj['dataset'],0)

  dec_vals = (out_vals-128.0)/128.0
  dec_bias = (out_bias)/128.0
  n = len(dec_vals)
  slope,intercept,rval,pval,stderr = \
                                     stats.linregress(dec_vals, \
                                                      dec_vals+dec_bias)
  pred = np.array(list(map(lambda v: slope*v+intercept,dec_vals)))
  errors = list(map(lambda i: dec_vals[i] + dec_bias[i] - pred[i], \
                   range(0,n)))

  model_out.bias = intercept
  model_out.gain = slope
  model_out.bias_uncertainty.from_data(errors,pred)
  upper = 1.0
  lower = -1.0
  sc_u = (upper+model_out.bias)/upper
  sc_l = (lower+model_out.bias)/lower
  model_out.set_oprange_scale(min(sc_u,sc_l), min(sc_u,sc_l))
  yield model_in
  yield model_out
