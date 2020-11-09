import hwlib.hcdc.llenums as enums
from hwlib.block import *
import ops.opparse as parser

lut = Block('lut',BlockType.COMPUTE, \
            [enums.NoModeType])

lut.modes.add_all([['*']])
lut.inputs.add(BlockInput('x', BlockSignalType.DIGITAL, \
                          ll_identifier=enums.PortType.NOPORT))
lut.outputs.add(BlockOutput('z', BlockSignalType.DIGITAL, \
                            ll_identifier=enums.PortType.NOPORT))

lut.data.add(BlockData('e', BlockDataType.EXPR, \
                       inputs=['y']))

func_impl = parser.parse_expr('e')
lut.outputs['z'].relation.bind(['_'], \
                               parser.parse_expr('f(x)',{
                                 'f':(['y'],func_impl)
                               }))

lut.inputs['x'] \
    .interval.bind(['*'],interval.Interval(-1,1))
lut.outputs['z'] \
    .interval.bind(['*'],interval.Interval(-1,1))
lut.inputs['x'] \
    .quantize.bind(['*'],Quantize(256,QuantizeType.LINEAR))
lut.outputs['z'] \
    .quantize.bind(['*'],Quantize(256,QuantizeType.LINEAR))

lut.state.add(BlockState('source', BlockStateType.CONNECTION, \
                        values=enums.LUTSourceType))
lut.state['source'].impl.incoming(sink_port="x", \
                                  source_block='adc', \
                                  source_loc=['_','_',0,0], \
                                  source_port='z', \
                                  value=enums.LUTSourceType.ADC0)

lut.state['source'].impl.incoming(sink_port="x", \
                                  source_block='adc', \
                                  source_loc=['_','_',2,0], \
                                  source_port='x', \
                                  value=enums.LUTSourceType.ADC1)

lut.state['source'].impl.set_default(enums.LUTSourceType.EXTERN)


