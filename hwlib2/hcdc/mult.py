import hwlib2.hcdc.llenums as enums
from hwlib2.block import *
import ops.opparse as parser
import ops.interval as interval

mult = Block('mult',BlockType.COMPUTE, \
            [enums.RangeType, \
             enums.RangeType, \
             enums.RangeType])

mult.modes.add_all([
  ['x','m','m'],
  ['x','m','h'],
  ['x','h','m'],
  ['x','h','h'],
  ['m','m','m'],
  ['m','h','m'],
  ['h','m','m'],
  ['m','m','h'],
  ['m','h','h'],
  ['h','m','h']
])

mult.inputs.add(BlockInput('x',BlockSignalType.ANALOG))
mult.inputs.add(BlockInput('y',BlockSignalType.ANALOG))
mult.outputs.add(BlockOutput('z',BlockSignalType.ANALOG))
mult.data.add(BlockData('c',BlockDataType.CONST))
mult.data['c'] \
    .interval.bind(['_','_','_'],interval.Interval(-1,1))
mult.data['c'] \
    .quantize.bind(['_','_','_'],Quantize(256,QuantizeType.LINEAR))

mult.outputs['z'].relation \
                 .bind(['x','m','m'],parser.parse_expr('c*x'))
mult.outputs['z'].relation \
                 .bind(['x','h','m'],parser.parse_expr('0.1*c*x'))


spec = DeltaSpec(parser.parse_expr('(a*c+b)*x + d'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=0.0)
spec.param('d',DeltaParamType.GENERAL,ideal=0.0)
mult.outputs['z'].deltas.bind(['x','_','_'],spec)


spec = DeltaSpec(parser.parse_expr('a*x*y + b'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.GENERAL,ideal=0.0)
mult.outputs['z'].deltas.bind(['m','_','_'],spec)
mult.outputs['z'].deltas.bind(['h','_','_'],spec)
