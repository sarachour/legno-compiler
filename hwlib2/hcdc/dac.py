import hwlib2.hcdc.llenums as enums
from hwlib2.block import *
import ops.opparse as parser

class HLDACSourceType(Enum):
  DYNAMIC = 'dynamic'
  CONST = 'const'

dac = Block('dac',BlockType.COMPUTE, \
            [HLDACSourceType,enums.RangeType])
dac.modes.add_all([
  [HLDACSourceType.DYNAMIC,enums.RangeType.MED],
  [HLDACSourceType.DYNAMIC,enums.RangeType.HIGH],
  [HLDACSourceType.CONST,enums.RangeType.MED],
  [HLDACSourceType.CONST,enums.RangeType.HIGH],

])
dac.inputs.add(BlockInput('x', BlockSignalType.DIGITAL))
dac.data.add(BlockData('c', BlockDataType.CONST))
dac.outputs.add(BlockOutput('z', BlockSignalType.ANALOG))

dac.outputs['z'].relation.bind([HLDACSourceType.DYNAMIC,'_'], \
                               parser.parse_expr('x'))
dac.outputs['z'].relation.bind([HLDACSourceType.CONST,'_'], \
                               parser.parse_expr('c'))

dac.codes.add(BlockCode('source', BlockCodeType.CONNECTION, \
                        values=enums.DACSourceType))
dac.codes['source'].impl.source('lut',['@','@',0,0],'x', \
                                enums.DACSourceType.LUT0)
dac.codes['source'].impl.source('lut',['@','@',2,0],'x', \
                                enums.DACSourceType.LUT1)
dac.codes['source'].impl.set_default(enums.DACSourceType.MEM)

