import compiler.infer_pass.infer_util as infer_util
import compiler.infer_pass.infer_visualize as infer_vis
import compiler.infer_pass.infer_fit as infer_fit
import lab_bench.lib.chipcmd.data as chipdata
import hwlib.hcdc.enums as spec_enums
from hwlib.model import PortModel

def build_config(meta):
  loc = infer_util.to_loc(meta['loc'])
  is_vga = infer_util.to_bool(meta['vga'])
  comp_mode = "vga" if is_vga else 'mul'
  if comp_mode == 'vga':
    scale_mode = (infer_util.to_range(meta['ranges']['in0']), \
                  infer_util.to_range(meta['ranges']['out0']))
    _,out = scale_mode
    max_unc = out.coeff()*0.04

  else:
    scale_mode = (infer_util.to_range(meta['ranges']['in0']), \
                  infer_util.to_range(meta['ranges']['in1']), \
                  infer_util.to_range(meta['ranges']['out0']))
    _,_,out = scale_mode
    max_unc = out.coeff()*0.05

  out = PortModel('multiplier',loc,'out', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode,
                  calib_obj=infer_util.CALIB_OBJ)

  in0 = PortModel('multiplier',loc,'in0', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode,
                  calib_obj=infer_util.CALIB_OBJ)
  in1 = PortModel('multiplier',loc,'in1',
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode,
                  calib_obj=infer_util.CALIB_OBJ)
  coeff = PortModel('multiplier',loc,'coeff', \
                    comp_mode=comp_mode, \
                    scale_mode=scale_mode,
                    calib_obj=infer_util.CALIB_OBJ)
  return scale_mode,max_unc,out,in0,in1,coeff


def infer(obj):
  result = build_config(obj['metadata'])
  scm,max_unc,model_out,model_in0,model_in1,model_coeff = result
  cm = model_out.comp_mode
  bnds = infer_fit.build_model(model_out,obj['dataset'],0,max_unc, \
                               kind="vga" if cm == "vga" else "affine")
  #print("[WARN] EMPIRICALLY, WE OBSERVE MULTIPLIER SCALED DOWN BY 0.87")
  #model_out.gain *= 0.87
  freq_gain = 1.0
  if cm == 'vga':
    #freq_gain = 0.95
    sci,sco = scm
    scale = sco.coeff()/sci.coeff()
    model_coeff.bias = model_out.gain_offset
    model_out.gain *= freq_gain
  else:
    #freq_gain = 0.85
    sci0,sci1,sco = scm
    model_out.gain *= freq_gain

  #upper = 2.0*sco.coeff()
  #lower = -2.0*sco.coeff()
  #sc_u = model_out.gain
  #sc_l = model_out.gain
  #model_out.set_oprange_scale(sc_u,sc_l)

  yield model_out
  yield model_in0
  yield model_in1
  yield model_coeff
  #input()
