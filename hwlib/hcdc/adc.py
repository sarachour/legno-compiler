import hwlib.hcdc.llenums as enums
from hwlib.block import *
import ops.opparse as parser

adc = Block('adc',BlockType.COMPUTE, \
            [enums.RangeType])
adc.modes.add_all([
  ['m'],
  ['h']

])
LOW_NOISE = 0.01
HIGH_NOISE = 0.1
adc.inputs.add(BlockInput('x', BlockSignalType.ANALOG, \
                          ll_identifier=enums.PortType.IN0))
adc.outputs.add(BlockOutput('z', BlockSignalType.DIGITAL, \
                            ll_identifier=enums.PortType.OUT0))

adc.outputs['z'].relation.bind(['m'], \
                               parser.parse_expr('0.5*x'))

adc.outputs['z'].relation.bind(['h'], \
                               parser.parse_expr('0.05*x'))
adc.inputs['x'] \
     .noise.bind(['m'],LOW_NOISE)
adc.inputs['x'] \
     .noise.bind(['h'],HIGH_NOISE)



MAX_FREQ = 40000.0
adc.outputs['z'] \
  .freq_limit.bind(['_'], MAX_FREQ)




adc.inputs['x'] \
    .interval.bind(['h'],interval.Interval(-20,20))

adc.inputs['x'] \
    .interval.bind(['m'],interval.Interval(-2,2))

adc.outputs['z'] \
    .interval.bind(['_'], interval.Interval(-1,1))
adc.outputs['z'] \
    .quantize.bind(['_'], Quantize(256,QuantizeType.LINEAR))


adc.state.add(BlockState('range',  \
                        state_type= BlockStateType.MODE, \
                        values=enums.RangeType,
))

adc.state['range'] \
   .impl.bind(['m'], enums.RangeType.MED)
adc.state['range'] \
   .impl.bind(['h'], enums.RangeType.HIGH)



def adc_calib_obj(spec):
  base_expr = 'abs((a-1.0))+abs(modelError)'
  base_expr += " + abs((b - round(b,{quantize})))"
  expr = base_expr.format(quantize=1.0/128)
  new_spec = spec.copy()
  new_spec.objective = parser.parse_expr(expr)
  return new_spec

def adc_calib_obj(spec):
  subobj = [
    ("abs((a-1.0))", 1, 0.05), \
    ("abs(modelError)", 1, 0.01), \
    ("abs(noise)", 1, 0.01), \
    ("abs(b)", 1, 0.01)
  ]
  new_spec = spec.copy()
  new_spec.objective = MultiObjective()
  for expr,priority,eps in subobj:
     new_spec.objective.add(parser.parse_expr(expr),
               priority=priority, \
               epsilon=eps)

  return new_spec




spec = DeltaSpec(parser.parse_expr('a*0.5*x+b'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
#spec.param('b',DeltaParamType.GENERAL,ideal=0.0)
new_spec = adc_calib_obj(spec)
adc.outputs['z'].deltas.bind(['m'],new_spec)

spec = DeltaSpec(parser.parse_expr('a*0.05*x+b'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
#spec.param('b',DeltaParamType.GENERAL,ideal=0.0)
new_spec = adc_calib_obj(spec)
adc.outputs['z'].deltas.bind(['h'],new_spec)



adc.state.add(BlockState('enable',
                         values=enums.BoolType, \
                         state_type=BlockStateType.CONSTANT))
adc.state['enable'].impl.bind(enums.BoolType.TRUE)

for field in ["test_en","test_adc","test_i2v","test_rs","test_rsinc"]:
  adc.state.add(BlockState(field,
                        values=enums.BoolType, \
                        state_type=BlockStateType.CONSTANT))
  adc.state[field].impl.bind(enums.BoolType.FALSE)


for field in ['i2v_cal','upper','lower']:
  adc.state.add(BlockState(field,
                          values=range(0,64), \
                          state_type=BlockStateType.CALIBRATE))
  adc.state[field].impl.set_default(16)



adc.state.add(BlockState('lower_fs',
                        values=range(0,4), \
                        state_type=BlockStateType.CALIBRATE))
adc.state['lower_fs'].impl.set_default(3)

adc.state.add(BlockState('upper_fs',
                        values=range(0,4), \
                        state_type=BlockStateType.CALIBRATE))
adc.state['upper_fs'].impl.set_default(3)

adc.state.add(BlockState('pmos2',
                        values=range(0,8), \
                        state_type=BlockStateType.CALIBRATE))
adc.state['pmos2'].impl.set_default(3)

adc.state.add(BlockState('pmos',
                        values=range(0,8), \
                        state_type=BlockStateType.CALIBRATE))
adc.state['pmos'].impl.set_default(3)

adc.state.add(BlockState('nmos',
                        values=range(0,8), \
                        state_type=BlockStateType.CALIBRATE))
adc.state['nmos'].impl.set_default(3)

