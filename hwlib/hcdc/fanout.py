import hwlib.hcdc.llenums as enums
from hwlib.block import *
import ops.interval as interval
import ops.opparse as parser

fan = Block('fanout',BlockType.ASSEMBLE, \
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
LOW_NOISE = 0.02
HIGH_NOISE = 0.04


p_in = fan.inputs.add(BlockInput('x',BlockSignalType.ANALOG, \
                          ll_identifier=enums.PortType.IN0))
p_out0 = fan.outputs.add(BlockOutput('z0',BlockSignalType.ANALOG, \
                            ll_identifier=enums.PortType.OUT0))
p_out1 = fan.outputs.add(BlockOutput('z1',BlockSignalType.ANALOG, \
                            ll_identifier=enums.PortType.OUT1))
p_out2 = fan.outputs.add(BlockOutput('z2',BlockSignalType.ANALOG, \
                            ll_identifier=enums.PortType.OUT2))
for port in [p_in,p_out0,p_out1,p_out2]:
  port.interval.bind(['_','_','_','m'],  \
                     interval.Interval(-2,2))
  port.interval.bind(['_','_','_','h'],  \
                     interval.Interval(-20,20))
  port.noise.bind(['_','_','_','m'],  \
                     LOW_NOISE)
  port.noise.bind(['_','_','_','h'],  \
                     HIGH_NOISE)

def fan_calib_obj(spec,idx,out):
  base_expr =  "{out}*abs(modelError)+{out}*abs(b{idx})"
  if idx == 0:
    base_expr += "+{deviate}*(abs((1.0-a{idx})))"

  expr = base_expr.format(out=1.0/out, \
                          deviate=0.005, \
                          idx=idx)
  spec.objective = parser.parse_expr(expr)
  return spec

def fan_calib_obj(spec,idx,out):
  subobjs = [ \
              ("abs(modelError)",1,1e-5), \
              ("abs(b{idx})",1,1e-5), \
             ("abs((1.0-a{idx}))",1,1e-5), \
              ("abs(noise)",1,1e-5)]

  obj = MultiObjective()
  for subobj,prio,eps  in subobjs:
    expr = subobj.format(out=out,idx=idx)
    obj.add(parser.parse_expr(expr),prio,eps) 

  spec.objective = obj
  return spec


for scale in ['m','h']:
  for idx,port in enumerate([p_out0,p_out1,p_out2]):
    pat = ['_','_','_',scale]
    pat[idx] = '+'
    fan.outputs[port.name].relation.bind(pat, parser.parse_expr('x'))
    spec = DeltaSpec(parser.parse_expr('a{idx}*x+b{idx}'.format(idx=idx)))
    #spec.param('a{idx}'.format(idx=idx),DeltaParamType.CORRECTABLE,ideal=1.0)
    spec.param('a{idx}'.format(idx=idx),DeltaParamType.GENERAL,ideal=1.0)
    spec.param('b{idx}'.format(idx=idx),DeltaParamType.GENERAL,ideal=0.0)
    fan_calib_obj(spec,idx,1.0 if scale == 'm' else 10.0)
    fan.outputs[port.name].deltas.bind(pat,spec)

    pat[idx] = '-'
    fan.outputs[port.name].relation.bind(pat, parser.parse_expr('-x'))
    spec = DeltaSpec(parser.parse_expr('-a{idx}*x+b{idx}'.format(idx=idx)))
    #spec.param('a{idx}'.format(idx=idx),DeltaParamType.CORRECTABLE,ideal=1.0)
    spec.param('a{idx}'.format(idx=idx),DeltaParamType.GENERAL,ideal=1.0)
    spec.param('b{idx}'.format(idx=idx),DeltaParamType.GENERAL,ideal=0.0)
    fan_calib_obj(spec,idx,1.0 if scale == 'm' else 10.0)
    fan.outputs[port.name].deltas.bind(pat,spec)


# Low level behavior

fan.state.add(BlockState('range',  \
                        state_type= BlockStateType.MODE, \
                        values=enums.RangeType,
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
'''
fan.state.add(BlockState('third', \
                        state_type=BlockStateType.CONNECTION, \
                        values=enums.BoolType))
fan.state['third'].impl.outgoing(source_port='z2', \
                                 sink_block='_', \
                                 sink_loc=['_','_','_','_'], \
                                 sink_port='_', \
                                 value=enums.BoolType.TRUE)
fan.state['third'].impl.set_default(enums.BoolType.FALSE)
'''

fan.state.add(BlockState('third',
                        values=enums.SignType, \
                        state_type=BlockStateType.CONSTANT))
fan.state['third'].impl.bind(enums.BoolType.TRUE)


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
                         values=range(0,64), \
                         length=5,\
                         default=32)


fan.state.add(BlockState('bias0',
                        values=range(0,64), \
                        index=enums.PortType.OUT0, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
fan.state['bias0'].impl.set_default(32)

fan.state.add(BlockState('bias1',
                        values=range(0,64), \
                        index=enums.PortType.OUT1, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
fan.state['bias1'].impl.set_default(32)
fan.state.add(BlockState('bias2',
                        values=range(0,64), \
                        index=enums.PortType.OUT2, \
                        array=calarr, \
                        state_type=BlockStateType.CALIBRATE))
fan.state['bias2'].impl.set_default(32)

assert(len(list(fan.modes)) > 0)
