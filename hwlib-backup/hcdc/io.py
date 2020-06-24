import itertools
import ops.op as ops
import util.util as gutil
import hwlib.units as units
from hwlib.block import Block, BlockType
import hwlib.props as props

import hwlib.hcdc.util as util
import hwlib.hcdc.globals as glb
import hwlib.hcdc.enums as enums

def dac_get_modes():
   opts = [
      [enums.SignType.POS],
      enums.RangeType.options()
   ]
   blacklist = [
      (None,enums.RangeType.LOW)
   ]
   modes = list(util.apply_blacklist(itertools.product(*opts),
                                     blacklist))
   return modes


def dac_is_standard(mode):
   sign,rng = mode
   return rng == enums.RangeType.MED

def dac_scale_model(dac):
   modes = dac_get_modes()
   std,nonstd = gutil.partition(dac_is_standard,modes)
   dac.set_scale_modes("*",std,glb.HCDCSubset.all_subsets())
   dac.set_scale_modes("*",nonstd,[glb.HCDCSubset.UNRESTRICTED, \
                                   glb.HCDCSubset.EXTENDED])
   for mode in modes:
      get_prop = lambda p : glb.CTX.get(p, dac.name,
                                    '*',mode,None)

      sign,rng = mode
      # ERRATA: dac does scale up.
      coeff = sign.coeff()*rng.coeff()*get_prop(glb.GLProp.COEFF)
      digital_props = util.make_dig_props(enums.RangeType.MED,
                                         get_prop(glb.GLProp.DIGITAL_INTERVAL),
                                         get_prop(glb.GLProp.DIGITAL_QUANTIZE)
      )
      ana_props = util.make_ana_props(rng,
                                      get_prop(glb.GLProp.CURRENT_INTERVAL))
      digital_props.set_continuous(0,get_prop(glb.GLProp.MAX_FREQ))
      digital_props.set_resolution(get_prop(glb.GLProp.DIGITAL_RESOLUTION))
      digital_props.set_coverage(get_prop(glb.GLProp.DIGITAL_COVERAGE))
      dac.set_coeff("*",mode,'out', coeff)
      dac.set_props("*",mode,["in"], digital_props)
      dac.set_props("*",mode,["out"], ana_props)


dac = Block('tile_dac',type=BlockType.DAC) \
                             .set_comp_modes(["*"], \
                                             glb.HCDCSubset.all_subsets()) \
                             .add_outputs(props.CURRENT,["out"]) \
                             .add_inputs(props.DIGITAL,["in"]) \
                             .set_op("*","out",ops.Var("in"))
dac_scale_model(dac)
dac.check()

def adc_get_modes():
   return [enums.RangeType.HIGH, enums.RangeType.MED]


def adc_is_standard(mode):
   return mode == enums.RangeType.MED


def adc_scale_model(adc):
   modes = adc_get_modes()
   std,nonstd = gutil.partition(adc_is_standard,modes)
   adc.set_scale_modes("*",std,glb.HCDCSubset.all_subsets())
   adc.set_scale_modes("*",nonstd,[glb.HCDCSubset.UNRESTRICTED, \
                                   glb.HCDCSubset.EXTENDED])
   for mode in modes:
      get_prop = lambda p : glb.CTX.get(p, adc.name,
                                    '*',mode,None)

      coeff = (1.0/mode.coeff())*get_prop(glb.GLProp.COEFF)
      analog_props = util.make_ana_props(mode,
                                         get_prop(glb.GLProp.CURRENT_INTERVAL))
      #analog_props.set_bandwidth(0,20,units.khz)

      digital_props = util.make_dig_props(enums.RangeType.MED,
                                          get_prop(glb.GLProp.DIGITAL_INTERVAL),
                                          get_prop(glb.GLProp.DIGITAL_QUANTIZE)
      )
      digital_props.set_resolution(get_prop(glb.GLProp.DIGITAL_RESOLUTION))
      digital_props.set_coverage(get_prop(glb.GLProp.DIGITAL_COVERAGE))
      digital_props.set_continuous(0,get_prop(glb.GLProp.MAX_FREQ))
      adc.set_props("*",mode,["in"],analog_props)
      adc.set_props("*",mode,["out"], digital_props)
      adc.set_coeff("*",mode,'out', coeff)



adc = Block('tile_adc',type=BlockType.ADC) \
                             .set_comp_modes(["*"], \
                                             glb.HCDCSubset.all_subsets()) \
                             .add_outputs(props.DIGITAL,["out"]) \
                             .add_inputs(props.CURRENT,["in"]) \
                             .set_op("*","out",ops.Var("in")) \
                             .set_props("*","*",["out"],None) \
                             .set_props("*","*",["in"],None) \
                             .set_coeff("*","*","out",0.5)
adc_scale_model(adc)
adc.check()
