
class DiffPinMode:

  def __init__(self,low_pin,high_pin):
    self.low= low_pin
    self.high= high_pin


class HWEnv:
  class OscEnv:

    def __init__(self):
      self._ranges = {}
      self._outputs = {}
      pass

    def chan_ranges(self):
      for chan,(low,high) in self._ranges.items():
        yield chan,low,high

    def chan_range(self,chan):
      return self._ranges[chan]

    def add_range(self,chan,low,high):
      self._ranges[chan] = (low,high)

    def add_output(self,pinmode,handle):
      self._outputs[handle] = pinmode

    def output(self,handle):
      return self._outputs[handle]

    def outputs(self):
      return self._outputs.keys()

  def __init__(self,name):
    self.name = name
    self._osc = None
    self._dacs = {}
    self._adcs = {}
    self._manual = False

  @property
  def manual(self):
    return self._manual

  def set_manual(self,v):
    self._manual = v

  def dac(self,handle):
    return self._dacs[handle]

  def adc(self,handle):
    if not handle in self._adcs:
      return None

    return self._adcs[handle]

  def dacs(self):
    for handle,due_dac in self._dacs.items():
      yield handle,due_dac


  def adcs(self):
    for handle,due_adc in self._adcs.items():
      yield handle,due_adc

  @property
  def oscilloscope(self):
    return self._osc

  def add_adc(self,due_adc,handle):
    self._adcs[handle] = due_adc


  def add_dac(self,due_dac,handle):
    self._dacs[handle] = due_dac

  def use_oscilloscope(self):
    assert(self._osc is None)
    self._osc = HWEnv.OscEnv()
    return self._osc
