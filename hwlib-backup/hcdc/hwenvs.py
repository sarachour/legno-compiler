from hwlib.hwenv import HWEnv, DiffPinMode
from hwlib.units import mV

def noosc():
  exp = HWEnv('noosc')
  #osc = exp.use_oscilloscope()

  exp.add_dac(due_dac=0,handle='D0')
  exp.add_dac(due_dac=1,handle='D1')
  # read one value with oscilloscope, 3 with adc
  exp.add_adc(due_adc=0,handle="A0")
  exp.add_adc(due_adc=1,handle="A1")
  exp.add_adc(due_adc=2,handle="A2")
  exp.add_adc(due_adc=3,handle="A3")
  return exp

def microphone():
  exp = HWEnv('audio')
  osc = exp.use_oscilloscope()
  osc.add_range(0,102*mV,1310*mV)
  osc.add_range(1,102*mV,1310*mV)
  exp.set_manual(True)
  exp.add_dac(due_dac=0,handle='D0')
  exp.add_dac(due_dac=1,handle='D1')
  # read one value with oscilloscope, 3 with adc
  osc.add_output(DiffPinMode(0,1),handle="A0")
  osc.add_output(DiffPinMode(0,1),handle="A1")
  osc.add_output(DiffPinMode(0,1),handle="A2")
  osc.add_output(DiffPinMode(0,1),handle="A3")
  #exp.add_adc(due_adc=1,handle="A1")
  #exp.add_adc(due_adc=2,handle="A2")
  #exp.add_adc(due_adc=3,handle="A3")

  return exp


def default():
  exp = HWEnv('osc')
  osc = exp.use_oscilloscope()
  osc.add_range(0,102*mV,1310*mV)
  osc.add_range(1,102*mV,1310*mV)
  exp.add_dac(due_dac=0,handle='D0')
  exp.add_dac(due_dac=1,handle='D1')
  # read one value with oscilloscope, 3 with adc
  osc.add_output(DiffPinMode(0,1),handle="A0")
  osc.add_output(DiffPinMode(0,1),handle="A1")
  osc.add_output(DiffPinMode(0,1),handle="A2")
  osc.add_output(DiffPinMode(0,1),handle="A3")
  #exp.add_adc(due_adc=1,handle="A1")
  #exp.add_adc(due_adc=2,handle="A2")
  #exp.add_adc(due_adc=3,handle="A3")

  return exp


HW_ENVS = [
  default(),
  noosc(),
  microphone()
]

def get_hw_env(name):
  for exp in HW_ENVS:
    if exp.name == name:
      return exp

  raise Exception("unknown math_env <%s>" % name)
