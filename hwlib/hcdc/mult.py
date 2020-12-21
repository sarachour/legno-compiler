import hwlib.hcdc.llenums as enums
from hwlib.block import *
import ops.opparse as parser
import ops.interval as interval
import ops.generic_op as genoplib

def mkmodel(blk,terms):
  variables = list(map(lambda i: "c%d" % i, range(1,len(terms)+1))) \
              + ['c0']
  expr = ['c0']
  for coeff,term in zip(variables,terms):
    expr.append("%s*%s" % (coeff,term))
  expr_text = "+".join(expr)
  expr_ast = parser.parse_expr(expr_text)
  return PhysicalModelSpec.make(blk,expr_ast)

mult = Block('mult',BlockType.COMPUTE, \
            [enums.RangeType, \
             enums.RangeType, \
             enums.RangeType])

MODES = [
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
]



mult.modes.add_all(MODES)
LOW_NOISE = 0.02
HIGH_NOISE = 0.2


mult.inputs.add(BlockInput('x',BlockSignalType.ANALOG, \
                           ll_identifier=enums.PortType.IN0))
mult.inputs['x'] \
    .interval.bind(['_','m','_'],interval.Interval(-2,2))
mult.inputs['x'] \
    .interval.bind(['_','h','_'],interval.Interval(-20,20))
mult.inputs['x'] \
     .noise.bind(['_','m','_'],LOW_NOISE)
mult.inputs['x'] \
     .noise.bind(['_','h','_'],HIGH_NOISE)


mult.inputs.add(BlockInput('y',BlockSignalType.ANALOG, \
                           ll_identifier=enums.PortType.IN1))
mult.inputs['y'] \
    .interval.bind(['m','_','_'],interval.Interval(-2,2))
mult.inputs['y'] \
    .interval.bind(['x','_','_'],interval.Interval(-2,2))
mult.inputs['y'] \
    .interval.bind(['h','_','_'],interval.Interval(-20,20))
mult.inputs['y'] \
     .noise.bind(['m','_','_'],LOW_NOISE)
mult.inputs['y'] \
     .noise.bind(['h','_','_'],HIGH_NOISE)



mult.outputs.add(BlockOutput('z',BlockSignalType.ANALOG, \
                             ll_identifier=enums.PortType.OUT0))
mult.outputs['z'] \
    .interval.bind(['_','_','m'],interval.Interval(-2,2))
mult.outputs['z'] \
    .interval.bind(['_','_','h'],interval.Interval(-20,20))
mult.outputs['z'] \
     .noise.bind(['_','_','m'],LOW_NOISE)
mult.outputs['z'] \
     .noise.bind(['_','_','h'],HIGH_NOISE)




mult.data.add(BlockData('c',BlockDataType.CONST))
mult.data['c'] \
    .interval.bind(['_','_','_'],interval.Interval(-1,0.9921875))
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
                        values=range(0,64), \
                        state_type=BlockStateType.CALIBRATE))
mult.state['gain_cal'].impl.set_default(32)

calarr = BlockStateArray('port_cal', \
                         indices=enums.PortType, \
                         values=range(0,64), \
                         length=3,\
                         default=32)

mult.state.add(BlockState('bias_in0',
                        values=range(0,64), \
                        index=enums.PortType.IN0, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
mult.state['bias_in0'].impl.set_default(32)

mult.state.add(BlockState('bias_in1',
                        values=range(0,64), \
                        index=enums.PortType.IN1, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
mult.state['bias_in1'].impl.set_default(32)

mult.state.add(BlockState('bias_out',
                        values=range(0,64), \
                        index=enums.PortType.OUT0, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
mult.state['bias_out'].impl.set_default(32)


def vga_assign_calib_obj(spec,in0,out):
  #base_expr =  "((min(a,1.0))^(-1))*({out}*abs(modelError) + {out}*abs(v) + {out}*abs(u))"
  base_expr =  "{out}*abs(modelError) + {out}*abs(v) + {out}*abs(u) + 0.02*abs((a-1.0))"
  expr = base_expr.format(out=1.0/out, \
                          in0=1.0/in0)
  new_spec = spec.copy()
  new_spec.objective = parser.parse_expr(expr)
  return new_spec

spec = DeltaSpec(parser.parse_expr('(a*c+b)*x+c*u+v'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0)

new_spec = vga_assign_calib_obj(spec,1.0,1.0)
mult.outputs['z'].deltas.bind(['x','m','m'],new_spec)
new_spec = vga_assign_calib_obj(spec,10.0,10.0)
mult.outputs['z'].deltas.bind(['x','h','h'],new_spec)

#calib_obj = parser.parse_expr('((a)^(-1))*(modelError+d)')

spec = DeltaSpec(parser.parse_expr('0.1*(a*c+b)*x + 0.1*c*u + v'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0)
new_spec = vga_assign_calib_obj(spec,10.0,1.0)
mult.outputs['z'].deltas.bind(['x','h','m'],new_spec)


spec = DeltaSpec(parser.parse_expr('10.0*(a*c+b)*x + 10.0*u + v'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('b',DeltaParamType.LL_CORRECTABLE,ideal=0.0)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0)
new_spec = vga_assign_calib_obj(spec,1.0,10.0)
mult.outputs['z'].deltas.bind(['x','m','h'],new_spec)


def mul_assign_calib_obj(spec,in0,in1,out):
  base_expr =  "{out}*abs(modelError)+{in0}*abs(u)+{in1}*abs(v)+{out}*abs(w)"
  expr = base_expr.format(out=1.0/out, \
                          in0=1.0/in0, \
                          in1=1.0/in1)
  new_spec = spec.copy()
  new_spec.objective = parser.parse_expr(expr)
  return new_spec


spec = DeltaSpec(parser.parse_expr('0.5*a*(x+u)*(y+v) + w'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0)
spec.param('w',DeltaParamType.GENERAL,ideal=0.0)

new_spec = mul_assign_calib_obj(spec,1.0,1.0,1.0)
mult.outputs['z'].deltas.bind(['m','m','m'],new_spec)
new_spec = mul_assign_calib_obj(spec,1.0,10.0,10.0)
mult.outputs['z'].deltas.bind(['h','m','h'],new_spec)
new_spec = mul_assign_calib_obj(spec,10.0,1.0,10.0)
mult.outputs['z'].deltas.bind(['m','h','h'],new_spec)

spec = DeltaSpec(parser.parse_expr('5*a*(x+u)*(y+v) + w'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0)
spec.param('w',DeltaParamType.GENERAL,ideal=0.0)

new_spec = mul_assign_calib_obj(spec,1.0,1.0,10.0)
mult.outputs['z'].deltas.bind(['m','m','h'],new_spec)


spec = DeltaSpec(parser.parse_expr('0.05*a*(x+u)*(y+v) + w'))
spec.param('a',DeltaParamType.CORRECTABLE,ideal=1.0)
spec.param('u',DeltaParamType.GENERAL,ideal=0.0)
spec.param('v',DeltaParamType.GENERAL,ideal=0.0)
spec.param('w',DeltaParamType.GENERAL,ideal=0.0)

new_spec = mul_assign_calib_obj(spec,1.0,10.0,1.0)
mult.outputs['z'].deltas.bind(['h','m','m'],new_spec)
new_spec = mul_assign_calib_obj(spec,10.0,1.0,1.0)
mult.outputs['z'].deltas.bind(['m','h','m'],new_spec)
