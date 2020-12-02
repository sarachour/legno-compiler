import ops.op as ops
import hwlib.props as props
import hwlib.hcdc.enums as enums
import hwlib.hcdc.util as util
import hwlib.hcdc.globals as glb
import hwlib.units as units
from hwlib.hcdc.globals \
  import CTX, GLProp,HCDCSubset
from hwlib.block import Block,BlockType


ana_props = util.make_ana_props(enums.RangeType.HIGH,\
                                glb.CTX.get(glb.GLProp.CURRENT_INTERVAL,
                                            'tile_out', \
                                            "*","*",None))

tile_out = Block('tile_out',type=BlockType.BUS) \
                                  .set_comp_modes(["*"], \
                                                  HCDCSubset.all_subsets()) \
                                  .set_scale_modes("*",["*"], \
                                                   HCDCSubset.all_subsets()) \
                                  .add_outputs(props.CURRENT,["out"]) \
                                  .add_inputs(props.CURRENT,["in"]) \
                                  .set_op("*","out",ops.Var("in")) \
                                  .set_props("*","*",["out","in"], ana_props) \
                                  .set_coeff("*","*","out",1.0) \
                                  .check()
ana_props = util.make_ana_props(enums.RangeType.HIGH,\
                                CTX.get(GLProp.CURRENT_INTERVAL,
                                        'tile_in', \
                                        "*","*",None))

tile_in = Block('tile_in',type=BlockType.BUS) \
                                .set_comp_modes(["*"], \
                                                HCDCSubset.all_subsets()) \
                                  .set_scale_modes("*",["*"], \
                                                   HCDCSubset.all_subsets()) \
                                  .add_outputs(props.CURRENT,["out"]) \
                                  .add_inputs(props.CURRENT,["in"]) \
                                  .set_op("*","out",ops.Var("in")) \
                                  .set_props("*","*",["out","in"], ana_props) \
                                  .set_coeff("*","*","out",1.0) \
                                  .check()


ana_props = util.make_ana_props(enums.RangeType.HIGH,\
                                CTX.get(GLProp.CURRENT_INTERVAL,
                                        'conn_inv', \
                                        "*","*",None))

inv_conn = Block('conn_inv') \
           .set_comp_modes(["*"], \
                           HCDCSubset.all_subsets()) \
           .set_scale_modes("*",["*"], \
                            HCDCSubset.all_subsets()) \
           .add_outputs(props.CURRENT,["out"]) \
           .add_inputs(props.CURRENT,["in"]) \
           .set_op("*","out",ops.Var("in")) \
           .set_props("*","*",["out","in"], \
                      ana_props) \
           .set_coeff("*","*","out",-1.0) \
           .check()

ana_props = util.make_ana_props(enums.RangeType.HIGH,\
                                CTX.get(GLProp.CURRENT_INTERVAL,
                                        'chip_out', \
                                        "*","*",None))

chip_out = Block('chip_out',type=BlockType.BUS) \
                                  .set_comp_modes(["*"], \
                                                  HCDCSubset.all_subsets()) \
                                  .set_scale_modes("*",["*"], \
                                                   HCDCSubset.all_subsets()) \
                                  .add_outputs(props.CURRENT,["out"]) \
                                  .add_inputs(props.CURRENT,["in"]) \
                                  .set_op("*","out",ops.Var("in")) \
                                  .set_props("*","*",["out"], ana_props) \
                                  .set_props("*","*",["in"], ana_props) \
                                  .set_coeff("*","*","out",1.0) \
                                  .check()
ana_props = util.make_ana_props(enums.RangeType.HIGH,\
                                CTX.get(GLProp.CURRENT_INTERVAL,
                                        'chip_in', \
                                        "*","*",None))

chip_in = Block('chip_in',type=BlockType.BUS) \
                                 .set_comp_modes(["*"], \
                                                  HCDCSubset.all_subsets()) \
                                  .set_scale_modes("*",["*"], \
                                                   HCDCSubset.all_subsets()) \
                                  .add_outputs(props.CURRENT,["out"]) \
                                  .add_inputs(props.CURRENT,["in"]) \
                                  .set_op("*","out",ops.Var("in")) \
                                  .set_props("*","*",["in"], ana_props) \
                                  .set_props("*","*",["out"], ana_props) \
                                  .set_coeff("*","*","out",1.0) \
                                  .check()
