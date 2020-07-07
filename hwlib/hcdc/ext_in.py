import hwlib.hcdc.llenums as enums
from hwlib.block import *
import ops.opparse as parser

ext_in = Block('extin',BlockType.COMPUTE, \
            [enums.NoModeType])

ext_in.modes.add_all([["*"]])
ext_in.inputs.add(BlockInput('x', BlockSignalType.ANALOG, \
                              ll_identifier=enums.PortType.IN0))
ext_in.outputs.add(BlockOutput('z', BlockSignalType.ANALOG, \
                                ll_identifier=enums.PortType.OUT0))



factor = 2.0
ext_in.outputs['z'].relation.bind(["*"], \
                               parser.parse_expr('extvar((%s*x))' % factor))

ext_in.inputs['x'] \
       .interval.bind(["*"],interval.Interval(-2*factor,2*factor))
ext_in.outputs['z'] \
       .interval.bind(["*"],interval.Interval(-2,2))
