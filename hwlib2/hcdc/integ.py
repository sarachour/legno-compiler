import hwlib2.hcdc.llenums as enums
from hwlib2.block import *
import ops.opparse as parser
import ops.interval as interval

integ = Block('integ',BlockType.COMPUTE, \
            [enums.RangeType, \
             enums.RangeType, \
             enums.SignType])


integ.modes.add_all([
  ['m','m','+'],
  ['m','m','-'],
  ['m','h','+'],
  ['m','h','-'],
  ['h','m','+'],
  ['h','m','-'],
  ['h','h','+'],
  ['h','h','-']

])

integ.inputs.add(BlockInput('x',BlockSignalType.ANALOG, \
                           ll_identifier=enums.PortType.IN0))
integ.inputs['x'] \
    .interval.bind(['m','_','_'],interval.Interval(-2,2))
integ.inputs['x'] \
    .interval.bind(['h','_','_'],interval.Interval(-20,20))

integ.outputs.add(BlockOutput('z',BlockSignalType.ANALOG, \
                             ll_identifier=enums.PortType.OUT0))
integ.outputs['z'] \
    .interval.bind(['_','m','_'],interval.Interval(-2,2))
integ.outputs['z'] \
    .interval.bind(['_','h','_'],interval.Interval(-20,20))


integ.data.add(BlockData('z0',BlockDataType.CONST))
integ.data['z0'] \
    .interval.bind(['_','_','_'],interval.Interval(-1,1))
integ.data['z0'] \
    .quantize.bind(['_','_','_'],Quantize(256,QuantizeType.LINEAR))


integ.outputs['z'].relation \
                 .bind(['m','m','+'],parser.parse_expr('integ(x,(2.0*z0))'))

for field in ['enable']:
  integ.state.add(BlockState(field,
                          values=enums.BoolType, \
                          state_type=BlockStateType.CONSTANT))
  integ.state[field].impl.bind(enums.BoolType.TRUE)

for field in ['cal_enable']:
  integ.state.add(BlockState(field,
                          values=enums.BoolType, \
                          state_type=BlockStateType.CONSTANT))
  integ.state[field].impl.bind(enums.BoolType.FALSE)

bcarr = BlockStateArray('range', \
                        indices=enums.PortType, \
                        values=enums.RangeType, \
                        length=3,\
                        default=enums.RangeType.MED)

integ.state.add(BlockState('range_in',  \
                        state_type= BlockStateType.MODE, \
                         values=enums.RangeType, \
                         array=bcarr, \
                         index=enums.PortType.IN0))

integ.state['range_in'] \
   .impl.bind(['m','_','_'], enums.RangeType.MED)
integ.state['range_in'] \
   .impl.bind(['h','_','_'], enums.RangeType.HIGH)


integ.state.add(BlockState('range_out',  \
                          state_type= BlockStateType.MODE, \
                          values=enums.RangeType, \
                          array=bcarr, \
                          index=enums.PortType.OUT0))

integ.state['range_out'] \
   .impl.bind(['_','m','_'], enums.RangeType.MED)
integ.state['range_out'] \
   .impl.bind(['_','h','_'], enums.RangeType.HIGH)

