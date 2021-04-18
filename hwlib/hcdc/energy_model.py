from scipy import stats

#'adc_1khz':54.0*units.uW,
#'adc_20khz':82*units.uW,
#'dac_1khz':4.6*units.uW,
#'dac_20khz':20*units.uW,

def linear_model(x,y):
  slope,intercept,_,_,stderr = stats.linregress(x,y)
  return slope,intercept

uW = 1e-6
khz = 1000

freqs = [1.0*khz,20.0*khz]
adc_slope,dac_offset = linear_model(freqs, [54.0*uW,82.0*uW])
dac_slope,adc_offset = linear_model(freqs, [4.6*uW,20.0*uW])

# per hertz energy increase
FREQ_POWER= {
  'tile_adc':adc_slope,
  'tile_dac':dac_slope,
}

# per block power
BLOCK_POWER = {
  'fanout': 37.0*uW,
  'integ': 28.0*uW,
  'mult': 61.0*uW,
  'vga': 49.0*uW,
  'adc':adc_offset,
  'dac':dac_offset,
  'ext_chip_in': 0,
  'lut': 20.0*uW,
  'extout': 0,
  'extin':0,
  'tin':0,
  'cin':0,
  'tout':0,
  'cout':0,

}

GLOBAL_POWER = {
  'analog_leakage':6.7*uW,
  'digital_leakage':85.8*uW,
}
scf = 0.25
MODE_POWER_FACTOR = {
  'high': (1.0+scf),
  'low': (1.0-scf)
}

def nominal_global_power():
  return GLOBAL_POWER['analog_leakage'] + GLOBAL_POWER['digital_leakage']

def nominal_block_power(block,mode):
  if block == 'mult' and "x" in str(mode):
    nominal = BLOCK_POWER['vga']
  elif block == 'mult':
    nominal = BLOCK_POWER['mult']
  else:
    nominal = BLOCK_POWER[block]

  return nominal

def scale_mode_factor(block,scale_mode):
  if 'tile' in block or 'chip' in block:
    return 1.0

  if "h" in str(scale_mode):
    return MODE_POWER_FACTOR['high']

  if "l" in str(scale_mode):
    return MODE_POWER_FACTOR['low']

  return 1.0

def freq_power(circ,block,fmax):
  if block in FREQ_POWER:
    slope = FREQ_POWER[block]
    print("slope:%s" % slope)
    input()
  else:
    return 0

def compute_power(circ,bandwidth):
  power_figure = nominal_global_power()

  for cfg in circ.configs:
    block = cfg.inst.block
    nominal = nominal_block_power(block,cfg.mode)
    scm_factor = scale_mode_factor(block,cfg.mode)
    freq = freq_power(circ,block,bandwidth)
    power = nominal*scm_factor+freq
    power_figure += power

  return power_figure

