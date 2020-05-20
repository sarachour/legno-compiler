import hwlib2.hcdc.llenums as enums
from hwlib2.block import *
import ops.opparse as parser

lut = Block('lut',BlockType.COPY, \
            [str])

lut.modes.add_all([['*']])
lut.inputs.add(BlockInput('x', BlockSignalType.DIGITAL))
lut.outputs.add(BlockOutput('z', BlockSignalType.DIGITAL))

lut.data.add(BlockData('f', BlockDataType.EXPR,inputs=1))
lut.outputs['z'].relation.bind(['_'], \
                               parser.parse_expr('f(x)'))

lut.state.add(BlockState('source', BlockStateType.CONNECTION, \
                        values=enums.LUTSourceType))
lut.state['source'].impl.source('adc',['@','@',0,0],'x', \
                           enums.LUTSourceType.ADC0)
lut.state['source'].impl.source('adc',['@','@',2,0],'x', \
                           enums.LUTSourceType.ADC1)
lut.state['source'].impl.set_default(enums.LUTSourceType.EXTERN)


