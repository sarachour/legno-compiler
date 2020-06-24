import hwlib.hcdc.llenums as enums
from hwlib.block import *
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

mult.inputs.add(BlockInput('x',BlockSignalType.ANALOG, \
                           ll_identifier=enums.PortType.IN0))
mult.inputs['x'] \
    .interval.bind(['_','m','_'],interval.Interval(-2,2))
mult.inputs['x'] \
    .interval.bind(['_','h','_'],interval.Interval(-2,2))

mult.inputs.add(BlockInput('y',BlockSignalType.ANALOG, \
                           ll_identifier=enums.PortType.IN1))
mult.inputs['y'] \
    .interval.bind(['m','_','_'],interval.Interval(-2,2))
mult.inputs['y'] \
    .interval.bind(['x','_','_'],interval.Interval(-2,2))
mult.inputs['y'] \
    .interval.bind(['h','_','_'],interval.Interval(-20,20))


mult.outputs.add(BlockOutput('z',BlockSignalType.ANALOG, \
                             ll_identifier=enums.PortType.OUT0))
mult.outputs['z'] \
    .interval.bind(['_','_','m'],interval.Interval(-2,2))
mult.outputs['z'] \
    .interval.bind(['_','_','h'],interval.Interval(-20,20))



mult.data.add(BlockData('c',BlockDataType.CONST))
mult.data['c'] \
    .interval.bind(['_','_','_'],interval.Interval(-1,1))
mult.data['c'] \
    .quantize.bind(['_','_','_'],Quantize(256,QuantizeType.LINEAR))

mult.outputs['z'].relation \
                 .bind(['x','m','m'],parser.parse_expr('c*x'))
mult.outputs['z'].relation \
                 .bind(['x','m','h'],parser.parse_expr('10.0*c*x'))
mult.outputs['z'].relation \
                 .bind(['x','h','m'],parser.parse_expr('0.1*c*x'))
mult.outputs['z'].relation \
                 .bind(['x','h','h'],parser.parse_expr('c*x'))
mult.outputs['z'].relation \
                 .bind(['m','m','m'],parser.parse_expr('0.5*x*y'))
mult.outputs['z'].relation \
                 .bind(['h','m','h'],parser.parse_expr('0.5*x*y'))
mult.outputs['z'].relation \
                 .bind(['m','h','h'],parser.parse_expr('0.5*x*y'))
mult.outputs['z'].relation \
                 .bind(['m','m','h'],parser.parse_expr('5.0*x*y'))
mult.outputs['z'].relation \
                 .bind(['h','m','m'],parser.parse_expr('0.05*x*y'))
mult.outputs['z'].relation \
                 .bind(['m','h','m'],parser.parse_expr('0.05*x*y'))



spec = DeltaSpec(parser.parse_expr('(a*c+b)*x + d'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=0.0)
spec.param('d',DeltaParamType.GENERAL,ideal=0.0)
mult.outputs['z'].deltas.bind(['x','m','m'],spec)
mult.outputs['z'].deltas.bind(['x','h','h'],spec)

spec = DeltaSpec(parser.parse_expr('0.1*(a*c+b)*x + d'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=0.0)
spec.param('d',DeltaParamType.GENERAL,ideal=0.0)
mult.outputs['z'].deltas.bind(['x','h','m'],spec)


spec = DeltaSpec(parser.parse_expr('10.0*(a*c+b)*x + d'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=0.0)
spec.param('d',DeltaParamType.GENERAL,ideal=0.0)
mult.outputs['z'].deltas.bind(['x','m','h'],spec)


spec = DeltaSpec(parser.parse_expr('0.5*a*x*y + b'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.GENERAL,ideal=0.0)
mult.outputs['z'].deltas.bind(['m','m','m'],spec)
mult.outputs['z'].deltas.bind(['h','m','h'],spec)
mult.outputs['z'].deltas.bind(['m','h','h'],spec)

# bind codes, range
mult.state.add(BlockState('enable',
                        values=enums.SignType, \
                        state_type=BlockStateType.CONSTANT))
mult.state['enable'].impl.bind(enums.BoolType.TRUE)

# vga
mult.state.add(BlockState('vga',  \
                        state_type= BlockStateType.MODE, \
                        values=enums.BoolType))
mult.state['vga'] \
   .impl.bind(['x','_','_'], enums.BoolType.TRUE)
mult.state['vga'] \
   .impl.bind(['m','_','_'], enums.BoolType.FALSE)
mult.state['vga'] \
   .impl.bind(['h','_','_'], enums.BoolType.FALSE)

bcarr = BlockStateArray('range', \
                        indices=enums.PortType, \
                        values=enums.RangeType, \
                        length=3,\
                        default=enums.RangeType.MED)

mult.state.add(BlockState('range_in0',  \
                        state_type= BlockStateType.MODE, \
                         values=enums.RangeType, \
                         array=bcarr, \
                         index=enums.PortType.IN0))

mult.state['range_in0'] \
   .impl.bind(['_','m','_'], enums.RangeType.MED)
mult.state['range_in0'] \
   .impl.bind(['_','h','_'], enums.RangeType.HIGH)

mult.state.add(BlockState('range_in1',  \
                          state_type= BlockStateType.MODE, \
                          values=enums.RangeType, \
                          array=bcarr, \
                          index=enums.PortType.IN1))

mult.state['range_in1'] \
   .impl.bind(['m','_','_'], enums.RangeType.MED)
mult.state['range_in1'] \
   .impl.bind(['h','_','_'], enums.RangeType.HIGH)
mult.state['range_in1'] \
   .impl.bind(['x','_','_'], enums.RangeType.MED)


mult.state.add(BlockState('range_out',  \
                          state_type= BlockStateType.MODE, \
                          values=enums.RangeType, \
                          array=bcarr, \
                          index=enums.PortType.OUT0))

mult.state['range_out'] \
   .impl.bind(['_','_','m'], enums.RangeType.MED)
mult.state['range_out'] \
   .impl.bind(['_','_','h'], enums.RangeType.HIGH)




mult.state.add(BlockState('gain_code',
                          values=range(0,256), \
                          state_type=BlockStateType.DATA))
mult.state['gain_code'].impl.set_variable('c')
mult.state['gain_code'].impl.set_default(128)



mult.state.add(BlockState('pmos',
                        values=range(0,8), \
                        state_type=BlockStateType.CALIBRATE))
mult.state['pmos'].impl.set_default(3)

mult.state.add(BlockState('nmos',
                        values=range(0,8), \
                        state_type=BlockStateType.CALIBRATE))
mult.state['nmos'].impl.set_default(3)

# gain_code

mult.state.add(BlockState('gain_cal',
                        values=range(0,32), \
                        state_type=BlockStateType.CALIBRATE))
mult.state['gain_cal'].impl.set_default(16)

calarr = BlockStateArray('port_cal', \
                         indices=enums.PortType, \
                         values=range(0,32), \
                         length=3,\
                         default=16)

mult.state.add(BlockState('bias_in0',
                        values=range(0,32), \
                        index=enums.PortType.IN0, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
mult.state['bias_in0'].impl.set_default(16)

mult.state.add(BlockState('bias_in1',
                        values=range(0,32), \
                        index=enums.PortType.IN1, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
mult.state['bias_in1'].impl.set_default(16)

mult.state.add(BlockState('bias_out',
                        values=range(0,32), \
                        index=enums.PortType.OUT0, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
mult.state['bias_out'].impl.set_default(16)
