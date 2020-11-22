from scipy import optimize
import numpy as np
import math

def _compute_pct_nrmsd(ref_t,ref_x,meas_t,meas_x,debug=False):
  meas_x_reflow = np.interp(ref_t, meas_t, meas_x, left=0, right=0)
  MSE = np.sum((meas_x_reflow-ref_x)**2)/len(ref_t)
  RMSD = math.sqrt(MSE)
  # root mean squared error relative to full scale
  FS = float(max(ref_x) - min(ref_x))
  NRMSD = RMSD/FS
  PCT_NRMSD = NRMSD*100.0
  if debug:
    print("MSE=%e" % MSE)
    print("RMSD=%e" % RMSD)
    print("FS=%e" % FS)
    print("NRMSD=%f" % NRMSD)
    print("PCT_NRMSD=%f" % PCT_NRMSD)
  return PCT_NRMSD

def _apply_xform(t_meas,x_meas,model):
    a,b,c,d = model
    print(model)
    t_xform = a*t_meas - b
    x_xform = c*x_meas - d
    return t_xform,x_xform


def _clamp(xform,xform_spec,index):
    return min(max(xform[index], \
                   xform_spec[index][0]), \
               xform_spec[index][1])


def _compute_loss(tscaff, xscaff, tsig,xsig,xform_spec,xform):
    model = [_clamp(xform,xform_spec,0), \
             _clamp(xform,xform_spec,1),1.0,0]
    tsig_xform,xsig_xform = _apply_xform(tsig,xsig,model)
    err = _compute_pct_nrmsd(tscaff,xscaff, \
                             tsig_xform,xsig_xform, \
                             debug=False)
    return err

def align(scaffold,sig,xform_spec):
  import compiler.lwav_pass.waveform as wavelib
  n = 15
  def objfun(x):
      return _compute_loss(tscaff=np.array(scaffold.times), \
                           xscaff=np.array(scaffold.values), \
                           tsig=np.array(sig.times), \
                           xsig=np.array(sig.values), \
                           xform_spec=xform_spec, \
                           xform=x)

  time_coeff,time_offset = optimize.brute(objfun,xform_spec,Ns=n)
  tmeas_xform = time_coeff*np.array(sig.times) + time_offset
  return wavelib.Waveform(variable=sig.variable, \
                          times=tmeas_xform, \
                          values=sig.values, \
                          ampl_units=sig.ampl_units, \
                          time_units=sig.time_units, \
                          time_scale=sig.time_scale, \
                          mag_scale=sig.mag_scale)
