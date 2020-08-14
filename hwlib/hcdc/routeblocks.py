import hwlib.hcdc.llenums as enums
from hwlib.block import *
import ops.opparse as parser


cin= Block('cin',BlockType.ROUTE, \
            [enums.NoModeType])

cin.modes.add_all([['*']])
cin.inputs.add(BlockInput('x', BlockSignalType.ANALOG, \
                          ll_identifier=enums.PortType.IN0))
cin.outputs.add(BlockOutput('z', BlockSignalType.ANALOG, \
                            ll_identifier=enums.PortType.OUT0))

cin.outputs['z'].relation.bind(['_'], \
                               parser.parse_expr('x'))
cin.inputs['x'] \
    .interval.bind(['*'],interval.Interval(-20,20))
cin.outputs['z'] \
    .interval.bind(['*'],interval.Interval(-20,20))



cout= Block('cout',BlockType.ROUTE, \
            [enums.NoModeType])

cout.modes.add_all([['*']])
cout.inputs.add(BlockInput('x', BlockSignalType.ANALOG, \
                          ll_identifier=enums.PortType.IN0))
cout.outputs.add(BlockOutput('z', BlockSignalType.ANALOG, \
                            ll_identifier=enums.PortType.OUT0))

cout.outputs['z'].relation.bind(['_'], \
                               parser.parse_expr('x'))
cout.inputs['x'] \
    .interval.bind(['*'],interval.Interval(-20,20))
cout.outputs['z'] \
    .interval.bind(['*'],interval.Interval(-20,20))



tin= Block('tin',BlockType.ROUTE, \
            [enums.NoModeType])

tin.modes.add_all([['*']])
tin.inputs.add(BlockInput('x', BlockSignalType.ANALOG, \
                          ll_identifier=enums.PortType.IN0))
tin.outputs.add(BlockOutput('z', BlockSignalType.ANALOG, \
                            ll_identifier=enums.PortType.OUT0))

tin.outputs['z'].relation.bind(['_'], \
                               parser.parse_expr('x'))
tin.inputs['x'] \
    .interval.bind(['*'],interval.Interval(-20,20))
tin.outputs['z'] \
    .interval.bind(['*'],interval.Interval(-20,20))



tout= Block('tout',BlockType.ROUTE, \
            [enums.NoModeType])

tout.modes.add_all([['*']])
tout.inputs.add(BlockInput('x', BlockSignalType.ANALOG, \
                          ll_identifier=enums.PortType.IN0))
tout.outputs.add(BlockOutput('z', BlockSignalType.ANALOG, \
                            ll_identifier=enums.PortType.OUT0))

tout.outputs['z'].relation.bind(['_'], \
                               parser.parse_expr('x'))
tout.inputs['x'] \
    .interval.bind(['*'],interval.Interval(-20,20))
tout.outputs['z'] \
    .interval.bind(['*'],interval.Interval(-20,20))


