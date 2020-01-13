import numpy as np
import compiler.infer_pass.infer_util as infer_util
import compiler.infer_pass.infer_visualize as infer_vis
import compiler.infer_pass.infer_fit as infer_fit

from hwlib.model import PortModel

import matplotlib.pyplot as plt

def remove_outliers(data):
  Q1 = np.percentile(data, 25)
  Q3 = np.percentile(data, 75)
  IQR = Q3-Q1
  SCALE = 1.0
  UB = SCALE*IQR+Q3
  LB = Q1-SCALE*IQR

  idxs = filter(lambda i:data[i] <= UB and data[i] >= LB,
                     range(len(data)))

  print(UB,LB)
  return list(map(lambda i : data[i], idxs))

def build_config(meta):
  loc = infer_util.to_loc(meta['loc'])
  print(meta.keys())
  comp_mode =  infer_util.to_sign(meta['inv'])
  scale_mode = ( \
                 infer_util.to_range(meta['ranges']['in0']), \
                 infer_util.to_range(meta['ranges']['out0']) \
  )
  inp = PortModel('integrator',loc,'in', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode,
                  calib_obj=infer_util.CALIB_OBJ)
  out = PortModel('integrator',loc,'out', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode,
                  calib_obj=infer_util.CALIB_OBJ)
  out_z0 = PortModel('integrator',loc,'out', \
                     comp_mode=comp_mode, \
                     scale_mode=scale_mode, \
                     calib_obj=infer_util.CALIB_OBJ, \
                     handle=':z[0]')
  out_zp = PortModel('integrator',loc,'out', \
                     comp_mode=comp_mode, \
                     scale_mode=scale_mode, \
                     calib_obj=infer_util.CALIB_OBJ, \
                     handle=':z\'')
  out_z = PortModel('integrator',loc,'out', \
                    comp_mode=comp_mode, \
                    scale_mode=scale_mode, \
                    calib_obj=infer_util.CALIB_OBJ, \
                    handle=':z')
  ic = PortModel('integrator',loc,'ic', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode,
                 calib_obj=infer_util.CALIB_OBJ)
  return scale_mode,inp,ic,out,out_z,out_z0,out_zp


def infer(obj):
  scm,model_in,model_ic,model_out, \
    model_z,model_z0,model_zp = build_config(obj['metadata'])

  # fit initial condition model.
  insc,outsc = scm
  scale = outsc.coeff()/insc.coeff()
  bnds_ic = infer_fit.build_model(model_z0,obj['dataset'],0, \
                                  0.04)


  # estimate time constant
  cl_bias,cl_var,_,_,cl_zero = infer_util \
                     .get_data_by_mode(obj['dataset'],1)

  tc_errors,tc_R2,_,_,tcs_vals = infer_util \
                     .get_data_by_mode(obj['dataset'],2)

  ol_bias,ol_R2,_,_,ol_zero = infer_util \
                     .get_data_by_mode(obj['dataset'],3)

  ic_bias,ic_nz,_,_,ic_vals = infer_util \
                              .get_data_by_mode(obj['dataset'],0)


  tcs = []
  # correcting systematic time measurement issues
  correction = 1.0
  for tc_err,tc_val in zip(tc_errors,tcs_vals):
    tc=(tc_err+tc_val)/tc_val*correction
    tcs.append(tc)

  # update appropriate model
  tcs_lim=remove_outliers(tcs)
  mu,sigma = np.mean(tcs_lim),np.std(tcs_lim)
  if np.isnan(mu) or sigma > 0.01:
    model_z.enabled = False

  if not np.isnan(mu):
    model_z.gain = mu;
    model_z.gain_uncertainty.from_data(tcs_lim,tcs);
    model_z.bias = np.mean(ol_bias);
    model_z.bias_uncertainty.from_data(ol_bias,ol_zero);
    print("mean=%f std=%f" % (mu,sigma))


  if infer_util.about_one(model_z.gain) or True:
    model_z.gain = 1.0

  if infer_util.about_one(model_z0.gain):
    model_z0.gain = 1.0


  yield model_in
  yield model_ic
  yield model_out
  yield model_z
  yield model_zp
  yield model_z0
