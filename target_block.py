import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib

def get_dac_h(dev):
  block = dev.get_block('dac')
  inst = devlib.Location([0,1,2,0])
  cfg = adplib.BlockConfig.make(block,inst)
  cfg.modes = [block.modes.get(['const','h'])]
  cfg['nmos'].value = 7
  cfg['pmos'].value = 3
  cfg['gain_cal'].value = 63

  npts = 1343
  return block,inst,cfg


def get_dac_m(dev):
  block = dev.get_block('dac')
  inst = devlib.Location([0,1,2,0])
  cfg = adplib.BlockConfig.make(block,inst)
  cfg.modes = [block.modes.get(['const','m'])]
  cfg['nmos'].value = 7
  cfg['pmos'].value = 3
  cfg['gain_cal'].value = 63

  npts = -1
  return block,inst,cfg

def get_mult_mmm(dev):
  block = dev.get_block('mult')
  inst = devlib.Location([0,1,2,0])
  cfg = adplib.BlockConfig.make(block,inst)
  #cfg.modes = [['+','+','-','m']]
  cfg.modes = [block.modes.get(['m','m','m'])]

  cfg['pmos'].value = 0
  cfg['nmos'].value = 0
  cfg['gain_cal'].value = 0
  cfg['bias_in0'].value = 38
  cfg['bias_in1'].value = 32
  cfg['bias_out'].value = 22

  # this is probably a bug
  return block,inst,cfg


def get_mult_mm(dev):
  block = dev.get_block('mult')
  inst = devlib.Location([0,1,2,0])
  cfg = adplib.BlockConfig.make(block,inst)
  #cfg.modes = [['+','+','-','m']]
  cfg.modes = [block.modes.get(['x','m','m'])]

  cfg['pmos'].value = 0
  cfg['nmos'].value = 2
  cfg['gain_cal'].value = 0
  cfg['bias_in0'].value = 31
  cfg['bias_in1'].value = 32
  cfg['bias_out'].value = 15

  npts = -1
  return block,inst,cfg

def get_mult_hm(dev):
  # this has really high error for some reason... debug?
  block = dev.get_block('mult')
  inst = devlib.Location([0,1,2,0])
  cfg = adplib.BlockConfig.make(block,inst)
  #cfg.modes = [['+','+','-','m']]
  cfg.modes = [block.modes.get(['x','h','m'])]

  print("[WARN] not calibrated")
  cfg['pmos'].value = 1
  cfg['nmos'].value = 1
  cfg['gain_cal'].value = 0
  cfg['bias_in0'].value = 26
  cfg['bias_in1'].value = 32
  cfg['bias_out'].value = 17

  npts = 774978919
  return block,inst,cfg


def get_mult_mh(dev):
  # fixed. About 0.5% error
  block = dev.get_block('mult')
  inst = devlib.Location([0,1,2,0])
  cfg = adplib.BlockConfig.make(block,inst)
  cfg.modes = [block.modes.get(['x','m','h'])]

  print("[WARN] not calibrated")
  cfg['pmos'].value = 4
  cfg['nmos'].value = 0
  cfg['gain_cal'].value = 0
  cfg['bias_in0'].value = 37
  cfg['bias_in1'].value = 32
  cfg['bias_out'].value = 19

  npts = -1
  return block,inst,cfg


def get_block(dev):
  #return get_mult_mmm(dev)
  #return get_mult_mm(dev)
  #return get_mult_hm(dev)
  return get_mult_mh(dev)
  #return get_dac_h(dev)

