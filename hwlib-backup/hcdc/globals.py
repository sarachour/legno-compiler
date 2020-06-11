import util.util as util
import hwlib.units as units
import hwlib.hcdc.enums as enums
from enum import Enum
#NOMINAL_NOISE = 1e-9
#NOMINAL_DELAY = 1e-10

'''
TODO Calibration lessons

High units must be > 0.1 (gain of 0.08 caused it to crap out)
Email: is entire dynamic range -1.2V t0 1.2V used? Are A0 and A1 flipped? Initial condition experiments seem to indicate so.

integ/hi-hi: max-ic=0.81*10.0 (error is 0.02)
mult/hi-hi-/vga/gain-min: min-gain=0.2 (error is 0.02)


# issues to debug
integ/hi-hi: ic=0.4*10.0 (there's an issue with the initial condition not matching)
'''

class GLProp(Enum):
  CURRENT_INTERVAL = "curr_ival"
  VOLTAGE_INTERVAL = "volt_ival"
  DIGITAL_INTERVAL = "dig_ival"
  DIGITAL_QUANTIZE = "dig_quantize"
  DIGITAL_RESOLUTION = "dig_resolution"
  MAX_FREQ = "max_freq"
  DIGITAL_SAMPLE = "dig_samp"
  INBUF_SIZE = "in_buf"
  OUTBUF_SIZE = "out_buf"
  COEFF = "coeff"
  DIGITAL_COVERAGE = "coverage"

class HCDCSubset(Enum):
    STANDARD = "standard"
    UNRESTRICTED = "unrestricted"
    EXTENDED = "extended"

    @staticmethod
    def all_subsets():
      return [HCDCSubset.STANDARD,
              HCDCSubset.EXTENDED,
              HCDCSubset.UNRESTRICTED]

class GlobalCtx:

  def __init__(self):
    self._ctx = {}
    for prop in GLProp:
      self._ctx[prop] = {}
    self.freeze = False

  def __insert(self,prop,block,cm,sm,port,value):
    assert(not (block,cm,sm) in self._ctx[prop])
    self._ctx[prop][(block,cm,sm,port)] = value

  def get(self,prop,block,cm,sm,port):
    if (block,cm,sm,port) in self._ctx[prop]:
      return self._ctx[prop][(block,cm,sm,port)]

    if (block,cm,sm,None) in self._ctx[prop]:
      return self._ctx[prop][(block,cm,sm,None)]

    if (block,cm,None,None) in self._ctx[prop]:
      return self._ctx[prop][(block,cm,None,None)]

    if (block,None,None,None) in self._ctx[prop]:
      return self._ctx[prop][(block,None,None,None)]

    if (None,None,None,None) in self._ctx[prop]:
      return self._ctx[prop][(None,None,None,None)]

    raise Exception("no default value <%s>" % prop)

  def insert(self,prop,value,block=None,cm=None,sm=None,port=None):
    assert(not self.freeze)
    self.__insert(prop,block,cm,sm,port,value)

CTX = GlobalCtx()
trim = 1.0
CTX.insert(GLProp.DIGITAL_INTERVAL, (-1.0*trim,0.98*trim))
CTX.insert(GLProp.CURRENT_INTERVAL, (-2.0*trim,2.0*trim))
CTX.insert(GLProp.VOLTAGE_INTERVAL, (-1.0*trim,1.0*trim))
CTX.insert(GLProp.DIGITAL_QUANTIZE, 256)
CTX.insert(GLProp.DIGITAL_RESOLUTION, 1)
CTX.insert(GLProp.DIGITAL_COVERAGE, 1)

#max_freq_khz = 200
max_freq_khz = 200
#max_freq_khz = 150.00
#max_freq_khz = 40.00
adc_khz = 40.00
CTX.insert(GLProp.MAX_FREQ, max_freq_khz*units.khz)
CTX.insert(GLProp.DIGITAL_SAMPLE, 3.0*units.us)
CTX.insert(GLProp.INBUF_SIZE,1200)
CTX.insert(GLProp.OUTBUF_SIZE,1e9)
CTX.insert(GLProp.DIGITAL_COVERAGE , 1.0)

#freq_khz = 20
CTX.insert(GLProp.MAX_FREQ, adc_khz*units.khz, block='tile_dac')
CTX.insert(GLProp.COEFF, 2.0, block='tile_dac')

CTX.insert(GLProp.MAX_FREQ, adc_khz*units.khz, block='tile_adc')
CTX.insert(GLProp.COEFF, 0.5, block='tile_adc')
# leave padding around lookup table to prevent weird wraparound issues.
trim = 0.98
CTX.insert(GLProp.DIGITAL_INTERVAL, (-1.0*trim,0.98*trim),block='lut',port="out")
CTX.insert(GLProp.DIGITAL_INTERVAL, (-1.0*trim,0.98*trim),block='lut',port="in")

CTX.insert(GLProp.MAX_FREQ, adc_khz*units.khz, block='lut')

# specialized ext_chip_in
CTX.insert(GLProp.COEFF, 2.0, block='ext_chip_analog_in',cm="*",sm="*",port="out")

# specialized ext_chip_in
CTX.insert(GLProp.DIGITAL_QUANTIZE, 4096, block='ext_chip_in')
CTX.insert(GLProp.DIGITAL_COVERAGE, 0.0, block='ext_chip_in',cm="*",sm="*",port="in")
CTX.insert(GLProp.DIGITAL_SAMPLE, 10*units.us, block='ext_chip_in')

# specialized ext_chip_out

V2I_range = 1.208
DUE_range = 3.3/2.0
CTX.insert(GLProp.DIGITAL_QUANTIZE, 4096, block='ext_chip_out')
CTX.insert(GLProp.DIGITAL_SAMPLE, 1*units.ns, block='ext_chip_out')
CTX.insert(GLProp.COEFF, 0.5*V2I_range, block='ext_chip_out')
CTX.insert(GLProp.DIGITAL_COVERAGE, 0.0, block='ext_chip_out',cm="*",sm="*",port="out")
CTX.insert(GLProp.COEFF, 2.0, block='ext_chip_in',cm="*",sm="*",port="out")
CTX.insert(GLProp.DIGITAL_INTERVAL, (-DUE_range,DUE_range), \
           block='ext_chip_out')

CTX.freeze = True

cap_freq_khz = 126.00
TIME_FREQUENCY = cap_freq_khz*units.khz
