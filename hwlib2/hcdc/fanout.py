import hwlib2.hcdc.llenums as enums
from hwlib2.block import *
import ops.opparse as parser

fan = Block('fanout',BlockType.COPY, \
            [enums.SignType,enums.SignType,enums.SignType,enums.RangeType])
fan.modes.add_all([
  ['+','+','+','m'],
  ['+','+','-','m'],
  ['+','-','+','m'],
  ['-','+','+','m'],
  ['+','-','-','m'],
  ['-','+','-','m'],
  ['-','-','+','m'],
  ['-','-','-','m'],
  ['+','+','+','h'],
  ['+','+','-','h'],
  ['+','-','+','h'],
  ['-','+','+','h'],
  ['+','-','-','h'],
  ['-','+','-','h'],
  ['-','-','+','h'],
  ['-','-','-','h']
])

fan.inputs.add(BlockInput('x',BlockSignalType.ANALOG))
fan.outputs.add(BlockOutput('z0',BlockSignalType.ANALOG))
fan.outputs.add(BlockOutput('z1',BlockSignalType.ANALOG))
fan.outputs.add(BlockOutput('z2',BlockSignalType.ANALOG))

# High level behavior
fan.outputs['z0'].relation.bind(['+','_','_','_'], \
                                parser.parse_expr('x'))
spec = DeltaSpec(parser.parse_expr('a*x+b'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.GENERAL,ideal=0.0)
fan.outputs['z0'].deltas.bind(['+','_','_','_'],spec)

fan.outputs['z0'].relation.bind(['-','_','_','_'],\
                                parser.parse_expr('-x'))
spec = DeltaSpec(parser.parse_expr('-a*x+b'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.GENERAL,ideal=0.0)
fan.outputs['z0'].deltas.bind(['-','_','_','_'],spec)



# Low level behavior

fan.state.add(BlockState('range',  \
                        state_type= BlockStateType.MODE, \
                        values=enums.SignType,
))
bcarr = BlockStateArray('inv', \
                       indices=enums.PortType, \
                       values=enums.SignType, \
                       length=len(enums.PortType.ports()),\
                       default=enums.SignType.POS)

fan.state.add(BlockState('inv0',  \
                        state_type= BlockStateType.MODE, \
                        values=enums.SignType, \
                        array=bcarr, \
                        index=enums.PortType.OUT0))

fan.state.add(BlockState('inv1', \
                        state_type= BlockStateType.MODE, \
                        values=enums.SignType, \
                        array=bcarr,
                        index=enums.PortType.OUT1))

fan.state.add(BlockState('inv2', \
                        state_type= BlockStateType.MODE, \
                        values=enums.SignType, \
                        array=bcarr, \
                        index=enums.PortType.OUT2))

fan.state['inv0'] \
   .impl.bind(['+','_','_','_'], enums.SignType.POS)
fan.state['inv0'] \
   .impl.bind(['-','_','_','_'], enums.SignType.NEG)
fan.state['inv1'] \
   .impl.bind(['_','+','_','_'], enums.SignType.POS)
fan.state['inv1'] \
   .impl.bind(['_','-','_','_'], enums.SignType.NEG)
fan.state['inv2'] \
   .impl.bind(['_','_','+','_'], enums.SignType.POS)
fan.state['inv2'] \
   .impl.bind(['_','_','-','_'], enums.SignType.NEG)
fan.state['range'] \
  .impl.bind(['_','_','_','m'], enums.RangeType.MED)
fan.state['range'] \
  .impl.bind(['_','_','_','h'], enums.RangeType.HIGH)

fan.state.add(BlockState('third', \
                        state_type=BlockStateType.CONNECTION, \
                        values=enums.BoolType))
fan.state['third'].impl.sink('z2','_',['_','_','_','_','_'], \
                             enums.BoolType.TRUE)
fan.state['third'].impl.set_default(enums.BoolType.FALSE)

fan.state.add(BlockState('enable',
                        values=enums.SignType, \
                        state_type=BlockStateType.CONSTANT))
fan.state['enable'].impl.bind(enums.BoolType.TRUE)

fan.state.add(BlockState('pmos',
                        values=range(0,8), \
                        state_type=BlockStateType.CALIBRATE))
fan.state['pmos'].impl.set_default(3)
fan.state.add(BlockState('nmos',
                        values=range(0,8), \
                        state_type=BlockStateType.CALIBRATE))
fan.state['nmos'].impl.set_default(3)

calarr = BlockStateArray('port_cal', \
                         indices=enums.PortType, \
                         values=range(0,32), \
                         length=len(enums.PortType.ports()),\
                         default=16)


fan.state.add(BlockState('bias0',
                        values=range(0,32), \
                        index=enums.PortType.OUT0, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))

fan.state['bias0'].impl.set_default(16)
fan.state.add(BlockState('bias1',
                        values=range(0,32), \
                        index=enums.PortType.OUT1, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
fan.state['bias1'].impl.set_default(16)
fan.state.add(BlockState('bias2',
                        values=range(0,32), \
                        index=enums.PortType.OUT2, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
fan.state['bias2'].impl.set_default(16)

