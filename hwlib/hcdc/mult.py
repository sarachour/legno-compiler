import ops.op as ops

from hwlib.block import Block
import hwlib.props as props
import hwlib.units as units

import util.util as gutil
import hwlib.hcdc.util as util
import hwlib.hcdc.globals as glb
import hwlib.hcdc.enums as enums

import itertools

# 10.0 >= coeff >= 0.1
# 10.0 >= in0 >= 0.1
# 10.0 >= in1 >= 0.1
# 10.0 >= out >= 0.1
# out = in0*in1*coeff

def get_modes():
  opts_mult = [
    list(enums.RangeType.options()),
    list(enums.RangeType.options()),
    list(enums.RangeType.options())
  ]

  opts_vga = [
    list(enums.RangeType.options()),
    list(enums.RangeType.options())
  ]

  blacklist_vga = []
  ub = 10.0
  lb = 0.1
  for inp,out in itertools.product(*opts_vga):
    scf = out.coeff()/inp.coeff()
    if scf > ub or scf < lb or \
       inp == enums.RangeType.LOW:
      blacklist_vga.append((inp,out))

  blacklist_mult = []
  for inp0,inp1,out in itertools.product(*opts_mult):
    scf = out.coeff()/(inp0.coeff()*inp1.coeff())
    scf2 = inp0.coeff()/inp1.coeff()
    if scf < lb or scf > ub or \
       scf2 < lb or scf2 > ub or \
       inp0 == enums.RangeType.LOW or \
       inp1 == enums.RangeType.LOW:
      blacklist_mult.append((inp0,inp1,out))

  vga_modes = list(util.apply_blacklist(itertools.product(*opts_vga),
                                   blacklist_vga))
  mul_modes = list(util.apply_blacklist(itertools.product(*opts_mult),
                                   blacklist_mult))
  return vga_modes,mul_modes

def is_standard_vga(mode):
  i,o = mode
  return i == enums.RangeType.MED and \
    o == enums.RangeType.MED



def is_standard_mul(mode):
  i0,i1,o = mode
  return i0 == enums.RangeType.MED and \
    i1 == enums.RangeType.MED and \
    o == enums.RangeType.MED


def is_extended_vga(mode):
  i,o = mode
  #return (i == enums.RangeType.LOW or \
  not_low = (i != enums.RangeType.LOW) and \
          (o != enums.RangeType.LOW)
  disabled = []
  # produces bad config
  #disabled.append((enums.RangeType.HIGH,enums.RangeType.HIGH))
  #disabled.append((enums.RangeType.MED,enums.RangeType.HIGH))
  for ci,co in disabled:
    if i == ci and o == co:
      return False

  return not_low


def is_extended_mul(mode):
  i0,i1,o = mode
  not_low = i0 != enums.RangeType.LOW and \
                  i1 != enums.RangeType.LOW and \
                        o != enums.RangeType.LOW
 

  return not_low
  #return not_low


def scale_model(mult):
  vga_modes,mul_modes = get_modes()
  std,nonstd = gutil.partition(is_standard_mul,mul_modes)
  ext,_ = gutil.partition(is_extended_mul,mul_modes)
  mult.set_scale_modes("mul",std,glb.HCDCSubset.all_subsets())
  mult.set_scale_modes("mul",nonstd,[glb.HCDCSubset.UNRESTRICTED])
  mult.add_subsets("mul",ext,[glb.HCDCSubset.EXTENDED])

  std,nonstd = gutil.partition(is_standard_vga,vga_modes)
  ext,_ = gutil.partition(is_extended_vga,vga_modes)
  mult.set_scale_modes("vga",std,glb.HCDCSubset.all_subsets())
  mult.set_scale_modes("vga",nonstd,[glb.HCDCSubset.UNRESTRICTED])
  mult.add_subsets("vga",ext,[glb.HCDCSubset.EXTENDED])

  for mode in mul_modes:
      in0rng,in1rng,outrng = mode
      get_prop = lambda p : glb.CTX.get(p, mult.name,
                                    'mul',mode,None)
      # ERRATA: virtual scale of 0.5
      scf = 0.5*outrng.coeff()/(in0rng.coeff()*in1rng.coeff())
      dig_props = util.make_dig_props(enums.RangeType.MED, \
                                      get_prop(glb.GLProp.DIGITAL_INTERVAL),
                                      get_prop(glb.GLProp.DIGITAL_QUANTIZE))
      dig_props.set_constant()
      dig_props.set_resolution(get_prop(glb.GLProp.DIGITAL_RESOLUTION))
      mult.set_props("mul",mode,["in0"],
                    util.make_ana_props(in0rng,
                                        get_prop(glb.GLProp.CURRENT_INTERVAL)))
      mult.set_props("mul",mode,["in1"],
                    util.make_ana_props(in1rng,
                                        get_prop(glb.GLProp.CURRENT_INTERVAL)))
      mult.set_props("mul",mode,["coeff"], dig_props)
      mult.set_props("mul",mode,["out"],
                    util.make_ana_props(outrng,
                                        get_prop(glb.GLProp.CURRENT_INTERVAL)))
      mult.set_coeff("mul",mode,'out', scf)

  for mode in vga_modes:
      in0rng,outrng = mode
      # ERRATA: virtual scale of 0.5, but coefficient is scaled by two
      scf = outrng.coeff()/in0rng.coeff()
      get_prop = lambda p : glb.CTX.get(p, mult.name,
                                    'vga',mode,None)

      dig_props = util.make_dig_props(enums.RangeType.MED,\
                                      get_prop(glb.GLProp.DIGITAL_INTERVAL), \
                                      get_prop(glb.GLProp.DIGITAL_QUANTIZE))
      dig_props.set_constant()
      dig_props.set_resolution(get_prop(glb.GLProp.DIGITAL_RESOLUTION))
      mult.set_props("vga",mode,["in0"],
                    util.make_ana_props(in0rng, \
                                        get_prop(glb.GLProp.CURRENT_INTERVAL)
                    ))
      mult.set_props("vga",mode,["in1"],
                    util.make_ana_props(enums.RangeType.MED, \
                                        get_prop(glb.GLProp.CURRENT_INTERVAL)
                    ))
      mult.set_props("vga",mode,["coeff"], dig_props)
      mult.set_props("vga",mode,["out"],
                    util.make_ana_props(outrng, \
                                        get_prop(glb.GLProp.CURRENT_INTERVAL)
                    ))
      mult.set_coeff("vga",mode,'out', scf)



block = Block('multiplier') \
.set_comp_modes(["mul","vga"], glb.HCDCSubset.all_subsets()) \
.add_inputs(props.CURRENT,["in0","in1"]) \
.add_inputs(props.DIGITAL,["coeff"]) \
.add_outputs(props.CURRENT,["out"]) \
.set_op("mul","out",ops.Mult(ops.Var("in0"),ops.Var("in1"))) \
.set_op("vga","out",ops.Mult(ops.Var("coeff"),ops.Var("in0")))

scale_model(block)

block.check()

