import hwlib.hcdc.llenums as enums
from hwlib.block import *
import ops.opparse as parser
import ops.interval as interval

integ = Block('integ',BlockType.COMPUTE, \
            [enums.RangeType, \
             enums.RangeType, \
             enums.SignType])


MODES = [
  ['m','m','+'],
  ['m','m','-'],
  ['m','h','+'],
  ['m','h','-'],
  ['h','m','+'],
  ['h','m','-'],
  ['h','h','+'],
  ['h','h','-']
]
MODES = [
  ['m','m','+'],
  ['m','m','-'],
  ['h','m','+'],
  ['h','m','-'],
  ['h','h','+'],
  ['h','h','-']
]
integ.modes.add_all(MODES)
LOW_NOISE = 0.01
HIGH_NOISE = 0.1

MAX_FREQ = 80000.0

integ.inputs.add(BlockInput('x',BlockSignalType.ANALOG, \
                           ll_identifier=enums.PortType.IN0))
integ.inputs['x'] \
    .interval.bind(['m','_','_'],interval.Interval(-2,2))
integ.inputs['x'] \
     .noise.bind(['m','_','_'],LOW_NOISE)

integ.inputs['x'] \
    .interval.bind(['h','_','_'],interval.Interval(-20,20))
integ.inputs['x'] \
     .noise.bind(['h','_','_'],HIGH_NOISE)

integ.outputs.add(BlockOutput('z',BlockSignalType.ANALOG, \
                             ll_identifier=enums.PortType.OUT0))
integ.outputs['z'] \
    .interval.bind(['_','m','_'],interval.Interval(-2,2))
integ.outputs['z'] \
     .noise.bind(['_','m','_'],LOW_NOISE)

integ.outputs['z'] \
    .interval.bind(['_','h','_'],interval.Interval(-20,20))
integ.outputs['z'] \
     .noise.bind(['_','h','_'],HIGH_NOISE)


integ.outputs['z'] \
  .freq_limit.bind(['_','_','_'], MAX_FREQ)

integ.data.add(BlockData('z0',BlockDataType.CONST))

DEL = 1.0/128
integ.data['z0'] \
    .interval.bind(['_','_','_'],interval.Interval(-DEL*128,DEL*127))
integ.data['z0'] \
    .quantize.bind(['_','_','_'],Quantize(256,QuantizeType.LINEAR))


integ.outputs['z'].relation \
                 .bind(['m','m','+'],parser.parse_expr('integ(x,(2.0*z0))'))

integ.outputs['z'].relation \
                 .bind(['h','h','+'],parser.parse_expr('integ(x,(20.0*z0))'))


integ.outputs['z'].relation \
                 .bind(['m','h','+'],parser.parse_expr('integ((10.0*x),(20.0*z0))'))

integ.outputs['z'].relation \
                 .bind(['h','m','+'],parser.parse_expr('integ((0.1*x),(2.0*z0))'))
integ.outputs['z'].relation \
                 .bind(['m','m','-'],parser.parse_expr('-integ(x,(2.0*z0))'))

integ.outputs['z'].relation \
                 .bind(['h','h','-'],parser.parse_expr('-integ(x,(20.0*z0))'))


integ.outputs['z'].relation \
                 .bind(['m','h','-'],parser.parse_expr('-integ((10.0*x),(20.0*z0))'))

integ.outputs['z'].relation \
                 .bind(['h','m','-'],parser.parse_expr('-integ((0.1*x),(2.0*z0))'))

def integ_calib_obj(spec,out_scale):
  # u : this has high error... don't fit this
  base_expr = '{deviation2}*abs((b-1.0)) + {deviation}*abs((a-1.0)) + abs(modelError)*{gainOut} + {gainOut}*abs(v)'
  base_expr += " + abs(c)"
  expr = base_expr.format(gainOut=1.0/out_scale, \
                          deviation=0.2, \
                          deviation2=0.001, \
                          quantize=1.0/128.0)
  new_spec = spec.copy()
  new_spec.objective = parser.parse_expr(expr)
  return new_spec


def integ_calib_obj(spec,out_scale):
  # u : this has high error... don't fit this
  base_expr = '{deviation2}*abs((b-1.0)) + {deviation}*abs((a-1.0)) + abs(modelError)*{gainOut} + {gainOut}*abs(v)'
  base_expr += " + abs(c)"
  exprs = [
    "abs((a-1.0))",
    "abs((b-1.0))",
    "modelError/(a*{gainOut})",
    "abs(v)",
    "abs(c)"
  ]
  new_spec = spec.copy()
  new_spec.objective = DeltaSpec.MultiObjective()
  for expr in exprs:
    conc_expr = expr.format(gainOut=out_scale)
    new_spec.objective.add(parser.parse_expr(conc_expr))

  return new_spec


spec = DeltaSpec(parser.parse_expr('integ((a*x+v),(2.0*(b*z0+c)))'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('c',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_BIAS.value)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_STABLE.value)

new_spec = integ_calib_obj(spec,2.0)
integ.outputs['z'].deltas.bind(['m','m','+'],new_spec)

spec = DeltaSpec(parser.parse_expr('integ((-1*a*x+v),(-2.0*(b*z0+c)))'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('c',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_BIAS.value)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_STABLE.value)

new_spec = integ_calib_obj(spec,2.0)
integ.outputs['z'].deltas.bind(['m','m','-'],new_spec)


spec = DeltaSpec(parser.parse_expr('integ((a*x),(20.0*(b*z0+c)))'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('c',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_BIAS.value)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_STABLE.value)

new_spec = integ_calib_obj(spec,20.0)
integ.outputs['z'].deltas.bind(['h','h','+'],new_spec)


spec = DeltaSpec(parser.parse_expr('integ((-1*a*x),(-20.0*(b*z0+c)))'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('c',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_BIAS.value)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_STABLE.value)

new_spec = integ_calib_obj(spec,20.0)
integ.outputs['z'].deltas.bind(['h','h','-'],new_spec)



spec = DeltaSpec(parser.parse_expr('integ((10.0*a*x),(20.0*(b*z0+c)))'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('c',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_BIAS.value)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_STABLE.value)

new_spec = integ_calib_obj(spec,20.0)
integ.outputs['z'].deltas.bind(['m','h','+'],new_spec)

spec = DeltaSpec(parser.parse_expr('integ((-10.0*a*x),(-20.0*(b*z0+c)))'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('c',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_BIAS.value)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_STABLE.value)

new_spec = integ_calib_obj(spec,20.0)
integ.outputs['z'].deltas.bind(['m','h','-'],new_spec)



spec = DeltaSpec(parser.parse_expr('integ((0.1*a*x),(2.0*(b*z0+c)))'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('c',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_BIAS.value)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_STABLE.value)

new_spec = integ_calib_obj(spec,2.0)
integ.outputs['z'].deltas.bind(['h','m','+'],new_spec)


spec = DeltaSpec(parser.parse_expr('integ((-0.1*a*x),(-2.0*(b*z0+c)))'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('c',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_BIAS.value)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0, \
           label=enums.ProfileOpType.INTEG_DERIVATIVE_STABLE.value)

new_spec = integ_calib_obj(spec,2.0)
integ.outputs['z'].deltas.bind(['h','m','-'],new_spec)



integ.state.add(BlockState('ic_code',
                          values=range(0,256), \
                          state_type=BlockStateType.DATA))
integ.state['ic_code'].impl.set_variable('z0')
integ.state['ic_code'].impl.set_default(128)



for field in ['enable','exception']:
  integ.state.add(BlockState(field,
                          values=enums.BoolType, \
                          state_type=BlockStateType.CONSTANT))
  integ.state[field].impl.bind(enums.BoolType.TRUE)

bcarr = BlockStateArray('cal_enable', \
                        indices=enums.IntegCalEnIndex, \
                        values=enums.BoolType, \
                        length=3,\
                        default=enums.BoolType.FALSE)


for en_number in range(0,3):
  field = "cal_enable%d" % en_number
  integ.state.add(BlockState(field,
                             values=enums.BoolType, \
                             array=bcarr,
                             index=enums.IntegCalEnIndex.from_index(en_number),
                             state_type=BlockStateType.CONSTANT))
  integ.state[field].impl.bind(enums.BoolType.FALSE)


integ.state.add(BlockState('inv',  \
                           state_type= BlockStateType.MODE, \
                           values=enums.SignType))

integ.state['inv'] \
   .impl.bind(['_','_','+'], enums.SignType.POS)

integ.state['inv'] \
   .impl.bind(['_','_','-'], enums.SignType.NEG)



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


bcarr = BlockStateArray('port_cal', \
                        indices=enums.PortType, \
                        values=range(0,64), \
                        length=3,\
                        default=16)


integ.state.add(BlockState('port_cal_in',  \
                           state_type= BlockStateType.CALIBRATE, \
                           values=range(0,64), \
                           array=bcarr, \
                           index=enums.PortType.IN0))
integ.state['port_cal_in'].impl.set_default(16)


integ.state.add(BlockState('port_cal_out',  \
                           state_type= BlockStateType.CALIBRATE, \
                           values=range(0,64), \
                           array=bcarr, \
                           index=enums.PortType.OUT0))
integ.state['port_cal_out'].impl.set_default(16)

integ.state.add(BlockState('ic_cal',
                        values=range(0,64), \
                        state_type=BlockStateType.CALIBRATE))
integ.state['ic_cal'].impl.set_default(16)

integ.state.add(BlockState('pmos',
                        values=range(0,8), \
                        state_type=BlockStateType.CALIBRATE))
integ.state['pmos'].impl.set_default(3)
integ.state.add(BlockState('nmos',
                        values=range(0,8), \
                        state_type=BlockStateType.CALIBRATE))
integ.state['nmos'].impl.set_default(3)


