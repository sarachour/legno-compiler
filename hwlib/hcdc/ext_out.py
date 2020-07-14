import hwlib.hcdc.llenums as enums
from hwlib.block import *
import ops.opparse as parser

ext_out = Block('extout',BlockType.COMPUTE, \
            [enums.NoModeType])

ext_out.modes.add_all([["*"]])
ext_out.inputs.add(BlockInput('x', BlockSignalType.ANALOG, \
                              ll_identifier=enums.PortType.IN0))
ext_out.outputs.add(BlockOutput('z', BlockSignalType.ANALOG, \
                                ll_identifier=enums.PortType.OUT0))



factor = 1.2/2.0
ext_out.outputs['z'].relation.bind(["*"], \
                               parser.parse_expr('emit((%s*x))' % factor))

ext_out.inputs['x'] \
       .interval.bind(["*"],interval.Interval(-2,2))
ext_out.outputs['z'] \
       .interval.bind(["*"],interval.Interval(-2*factor,2*factor))
