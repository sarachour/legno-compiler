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

fan.codes.add(BlockCode('range',  \
                        code_type= BlockCodeType.MODE, \
                        values=enums.SignType,
))
bcarr = BlockCodeArray('inv', \
                       indices=enums.PortType, \
                       values=enums.SignType, \
                       length=len(enums.PortType),\
                       default=enums.SignType.POS)

fan.codes.add(BlockCode('inv0',  \
                        code_type= BlockCodeType.MODE, \
                        values=enums.SignType, \
                        array=bcarr, \
                        index=enums.PortType.OUT0))

fan.codes.add(BlockCode('inv1', \
                        code_type= BlockCodeType.MODE, \
                        values=enums.SignType, \
                        array=bcarr,
                        index=enums.PortType.OUT1))

fan.codes.add(BlockCode('inv2', \
                        code_type= BlockCodeType.MODE, \
                        values=enums.SignType, \
                        array=bcarr, \
                        index=enums.PortType.OUT2))

fan.codes['inv0'] \
   .impl.bind(['+','_','_','_'], enums.SignType.POS)
fan.codes['inv0'] \
   .impl.bind(['-','_','_','_'], enums.SignType.NEG)
fan.codes['inv1'] \
   .impl.bind(['_','+','_','_'], enums.SignType.POS)
fan.codes['inv1'] \
   .impl.bind(['_','-','_','_'], enums.SignType.NEG)
fan.codes['inv2'] \
   .impl.bind(['_','_','+','_'], enums.SignType.POS)
fan.codes['inv2'] \
   .impl.bind(['_','_','-','_'], enums.SignType.NEG)
fan.codes['range'] \
  .impl.bind(['_','_','_','m'], enums.RangeType.MED)
fan.codes['range'] \
  .impl.bind(['_','_','_','h'], enums.RangeType.HIGH)

fan.codes.add(BlockCode('third', \
                        code_type=BlockCodeType.CONNECTION, \
                        values=enums.BoolType))
fan.codes['third'].impl.sink('z2','_',['_','_','_','_','_'], \
                             enums.BoolType.TRUE)
fan.codes['third'].impl.set_default(enums.BoolType.FALSE)

fan.codes.add(BlockCode('enable',
                        values=enums.SignType, \
                        code_type=BlockCodeType.CONSTANT))
fan.codes['enable'].impl.bind(enums.BoolType.TRUE)

fan.codes.add(BlockCode('pmos',
                        values=range(0,8), \
                        code_type=BlockCodeType.CALIBRATE))
fan.codes['pmos'].impl.set_default(3)
fan.codes.add(BlockCode('nmos',
                        values=range(0,8), \
                        code_type=BlockCodeType.CALIBRATE))
fan.codes['nmos'].impl.set_default(3)

calarr = BlockCodeArray('port_cal', \
                       indices=enums.PortType, \
                       values=range(0,32), \
                       length=len(enums.PortType),\
                        default=16)


fan.codes.add(BlockCode('bias0',
                        values=range(0,32), \
                        index=enums.PortType.OUT0, \
                        array=calarr, \
                        code_type=BlockCodeType.CALIBRATE))
fan.codes['bias0'].impl.set_default(16)
fan.codes.add(BlockCode('bias1',
                        values=range(0,32), \
                        index=enums.PortType.OUT1, \
                        array=calarr, \
                        code_type=BlockCodeType.CALIBRATE))
fan.codes['bias1'].impl.set_default(16)
fan.codes.add(BlockCode('bias2',
                        values=range(0,32), \
                        index=enums.PortType.OUT2, \
                        array=calarr, \
                        code_type=BlockCodeType.CALIBRATE))
fan.codes['bias2'].impl.set_default(16)

