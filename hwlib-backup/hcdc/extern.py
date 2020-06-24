import ops.op as ops
from hwlib.block import Block, BlockType
import hwlib.props as props
import hwlib.units as units
import hwlib.hcdc.util as util
import hwlib.hcdc.globals as glb
import hwlib.hcdc.enums as enums



# DUE DAC -> VTOI
props_in = util.make_ana_props(enums.RangeType.MED,\
                                glb.CTX.get(glb.GLProp.VOLTAGE_INTERVAL,
                                        'ext_chip_analog_in', \
                                        "*","*",'in'))
props_in.set_physical(True)

props_out = util.make_ana_props(enums.RangeType.MED,\
                                glb.CTX.get(glb.GLProp.CURRENT_INTERVAL,
                                        'ext_chip_analog_in', \
                                        "*","*",'out'))
coeff = glb.CTX.get(glb.GLProp.COEFF,"ext_chip_analog_in",
                    "*","*","out")

block_analog_in = Block('ext_chip_analog_in') \
                  .set_comp_modes(["*"], \
                                  glb.HCDCSubset.all_subsets()) \
                  .set_scale_modes("*",["*"], \
                                   glb.HCDCSubset.all_subsets()) \
                  .add_outputs(props.CURRENT,["out"]) \
                  .add_inputs(props.CURRENT,["in"]) \
                  .set_op("*","out",ops.Var("in")) \
                  .set_props("*","*",["in"],props_in) \
                  .set_props("*","*",["out"], props_out) \
                  .set_coeff("*","*","out",coeff) \
                  .check()


# DUE DAC -> VTOI

coeff = glb.CTX.get(glb.GLProp.COEFF,"ext_chip_in",
                    "*","*","out")

props_in = util.make_dig_props(enums.RangeType.MED, \
                               glb.CTX.get( glb.GLProp.DIGITAL_INTERVAL, \
                                        'ext_chip_in', \
                                        "*","*",'in'), \
                               glb.CTX.get(glb.GLProp.DIGITAL_QUANTIZE, \
                                       'ext_chip_in', \
                                       "*","*","in"))
props_in.set_resolution(glb.CTX.get(glb.GLProp.DIGITAL_RESOLUTION,
                                 "ext_chip_in",
                                 "*","*",None))
props_in.set_coverage(glb.CTX.get(glb.GLProp.DIGITAL_COVERAGE, \
                                  "ext_chip_in", \
                                  "*","*","in"))
# sample rate is 10 us
props_in.set_clocked(glb.CTX.get(glb.GLProp.DIGITAL_SAMPLE, \
                             "ext_chip_in",
                             "*","*",None),
                     glb.CTX.get(glb.GLProp.INBUF_SIZE,
                             'ext_chip_in',
                             "*","*",None))

props_out = util.make_ana_props(enums.RangeType.HIGH,\
                                glb.CTX.get(glb.GLProp.CURRENT_INTERVAL,
                                        'ext_chip_in', \
                                        "*","*",'out'))
block_in = Block('ext_chip_in',type=BlockType.DAC) \
                                     .set_comp_modes(["*"], \
                                                     glb.HCDCSubset.all_subsets()) \
                                     .set_scale_modes("*",["*"], \
                                                      glb.HCDCSubset.all_subsets()) \
                                     .add_outputs(props.CURRENT,["out"]) \
                                     .add_inputs(props.DIGITAL,["in"]) \
                                     .set_op("*","out",ops.Var("in")) \
                                     .set_props("*","*",["in"],props_in) \
                                     .set_props("*","*",["out"], props_out) \
                                     .set_coeff("*","*","out",coeff) \
                                     .check()


coeff = glb.CTX.get(glb.GLProp.COEFF,"ext_chip_out",
                        "*","*","out")

# DUE ADC -> VTOI
props_out = util.make_dig_props(enums.RangeType.MED, \
                                         glb.CTX.get(glb.GLProp.DIGITAL_INTERVAL,
                                                 'ext_chip_out',
                                                 "*","*","out"),
                                         glb.CTX.get(glb.GLProp.DIGITAL_QUANTIZE,
                                                 "ext_chip_out",
                                                 "*","*",None))
props_out.set_resolution(glb.CTX.get(glb.GLProp.DIGITAL_RESOLUTION,
                                 "ext_chip_out",
                                 "*","*",None))
props_out.set_coverage(glb.CTX.get(glb.GLProp.DIGITAL_COVERAGE, \
                                  "ext_chip_out", \
                                  "*","*","out"))
#sample rate is 1 ns
props_out.set_clocked(glb.CTX.get(glb.GLProp.DIGITAL_SAMPLE, \
                              "ext_chip_out",
                              "*","*",None),
                     glb.CTX.get(glb.GLProp.OUTBUF_SIZE,
                             'ext_chip_out',
                             "*","*",None))

# for adc
#ext_chip_out_props.set_clocked(1,units.ns)
props_in = util.make_ana_props(enums.RangeType.MED,\
                                glb.CTX.get(glb.GLProp.CURRENT_INTERVAL,
                                        'ext_chip_out', \
                                        "*","*",'in'))
block_out = Block('ext_chip_out',type=BlockType.ADC) \
                                       .set_comp_modes(["*"], \
                                                       glb.HCDCSubset.all_subsets()) \
                                       .set_scale_modes("*",["*"], \
                                                        glb.HCDCSubset.all_subsets()) \
                                       .add_outputs(props.CURRENT,["out"]) \
                                       .add_inputs(props.CURRENT,["in"]) \
                                       .set_op("*","out",ops.Var("in")) \
                                       .set_props("*","*",["out"],props_out) \
                                       .set_props("*","*",["in"], props_in) \
                                       .set_coeff("*","*","out",coeff) \
                                       .check()
