import compiler.infer_pass.infer_util as infer_util
import compiler.infer_pass.infer_visualize as infer_vis
import compiler.infer_pass.infer_fit as infer_fit
import lab_bench.lib.chipcmd.data as chipcmd

from hwlib.model import PortModel

def build_config(meta):
  loc = infer_util.to_loc(meta['loc'])
  comp_mode = ( \
                 infer_util.to_sign(meta['invs']['out0']).value,
                 infer_util.to_sign(meta['invs']['out1']).value,
                 infer_util.to_sign(meta['invs']['out2']).value \
  )
  scale_mode = infer_util.to_range(meta['rng']).value
  print('fanout[%s]' % loc)
  if meta['third']:
    max_uncs = [0.01]*3
  else:
    max_uncs = [0.01]*3
    max_uncs[2] = 1.0

  out0 = PortModel('fanout',loc,'out0', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode,
                  calib_obj=infer_util.CALIB_OBJ)
  out1 = PortModel('fanout',loc,'out1', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode,
                  calib_obj=infer_util.CALIB_OBJ)
  out2 = PortModel('fanout',loc,'out2', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode,
                  calib_obj=infer_util.CALIB_OBJ)

  inp = PortModel('fanout',loc,'in', \
                  comp_mode=comp_mode, \
                  scale_mode=scale_mode, \
                  calib_obj=infer_util.CALIB_OBJ)

  return max_uncs,inp,out0,out1,out2

def infer(obj):
  max_uncs,model_in,model_out0,model_out1,model_out2 = \
                            build_config(obj['metadata'])

  bnds0 = infer_fit.build_model(model_out0, \
                                obj['dataset'],0,max_uncs[0])
  bnds1 = infer_fit.build_model(model_out1, \
                                obj['dataset'],1,max_uncs[1])
  bnds2 = infer_fit.build_model(model_out2, \
                                obj['dataset'],2,max_uncs[2])
  #bnds = infer_util.tightest_bounds([bnds0['in0'], \
  #                                   bnds1['in0'], \
  #                                   bnds2['in0']])
  #bnds = infer_util.normalize_bound(bnds,chipcmd.RangeType.MED)
  #model_in.set_oprange_scale(*bnds)


  if infer_util.about_one(model_out0.gain):
    model_out0.gain = 1.0

  if infer_util.about_one(model_out1.gain):
    model_out1.gain = 1.0

  if infer_util.about_one(model_out2.gain):
    model_out2.gain = 1.0

  model_out0.bias *= 2.0
  model_out1.bias *= 2.0
  model_out2.bias *= 2.0
  yield model_in
  yield model_out0
  yield model_out1
  yield model_out2
