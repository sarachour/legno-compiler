import util.util as gutil
import ops.op as ops
from hwlib.block import Block
import hwlib.props as props
import hwlib.units as units
import hwlib.hcdc.util as util
import hwlib.hcdc.enums as enums
import hwlib.hcdc.globals as glb

import itertools

def get_comp_modes():
  return enums.SignType.options()

def get_scale_modes():
  opts = [
    enums.RangeType.options(),
    enums.RangeType.options()
  ]
  blacklist = [
    (enums.RangeType.LOW,enums.RangeType.HIGH),
    (enums.RangeType.HIGH,enums.RangeType.LOW)
  ]
  modes = list(util.apply_blacklist(itertools.product(*opts),\
                                    blacklist))
  return modes


def is_standard(scale_mode):
  i,o = scale_mode
  return i == enums.RangeType.MED and \
    o == enums.RangeType.MED

def is_extended(scale_mode):
  i,o = scale_mode
  disabled = []
  # difficult to measure high values
  #disabled.append((enums.RangeType.MED,enums.RangeType.HIGH))
  for (ci,co) in disabled:
    if i == ci and o == co:
      return False

  return i != enums.RangeType.LOW and \
         o != enums.RangeType.LOW


def scale_model(integ):
  comp_modes = get_comp_modes()
  scale_modes = list(get_scale_modes())
  for comp_mode in comp_modes:
    standard,nonstandard = gutil.partition(is_standard,scale_modes)
    extended,_ = gutil.partition(is_extended,scale_modes)
    integ.set_scale_modes(comp_mode,standard,glb.HCDCSubset.all_subsets())
    integ.set_scale_modes(comp_mode,nonstandard,[glb.HCDCSubset.UNRESTRICTED])
    integ.add_subsets(comp_mode,extended,[glb.HCDCSubset.EXTENDED])
    for scale_mode in scale_modes:
      get_prop = lambda p : glb.CTX.get(p, integ.name,
                                    comp_mode,scale_mode,None)
      inrng,outrng = scale_mode
      analog_in = util.make_ana_props(inrng, \
                                      get_prop(glb.GLProp.CURRENT_INTERVAL))
      analog_in.set_bandwidth(0,get_prop(glb.GLProp.MAX_FREQ),units.hz)

      analog_out = util.make_ana_props(outrng, \
                                       get_prop(glb.GLProp.CURRENT_INTERVAL))
      dig_props = util.make_dig_props(enums.RangeType.MED,
                                      get_prop(glb.GLProp.DIGITAL_INTERVAL), \
                                      get_prop(glb.GLProp.DIGITAL_QUANTIZE))
      dig_props.set_constant()
      integ.set_props(comp_mode,scale_mode,['in'],analog_in)
      integ.set_props(comp_mode,scale_mode,["ic"], dig_props)
      integ.set_props(comp_mode,scale_mode,["out"],\
                      analog_out,
                      handle=":z[0]")
      integ.set_props(comp_mode,scale_mode,["out"],\
                      analog_out,
                      handle=":z")
      integ.set_props(comp_mode,scale_mode,["out"],
                      analog_out,
                      handle=":z'")
      integ.set_props(comp_mode,scale_mode,["out"],
                      analog_out)

      scf_inout = outrng.coeff()/inrng.coeff()
      # alteration: initial condition, is not scaled
      scf_ic = outrng.coeff()*2.0
      integ.set_coeff(comp_mode,scale_mode,"out",scf_inout,handle=':z\'')
      integ.set_coeff(comp_mode,scale_mode,"out",scf_ic,':z[0]')
      integ.set_coeff(comp_mode,scale_mode,"out",1.0,handle=':z')
      integ.set_coeff(comp_mode,scale_mode,"out",1.0)

block = Block('integrator',) \
.set_comp_modes(get_comp_modes(),glb.HCDCSubset.all_subsets()) \
.add_inputs(props.CURRENT,["in","ic"]) \
.add_outputs(props.CURRENT,["out"]) \
.set_op(enums.SignType.POS,"out",
        ops.Integ(ops.Var("in"), ops.Var("ic"),
                  handle=':z'
        )
) \
.set_op(enums.SignType.NEG,"out",
        ops.Integ(ops.Mult(ops.Const(-1),ops.Var("in")), \
        ops.Var("ic"),
        handle=':z')
)
scale_model(block)
block.check()

