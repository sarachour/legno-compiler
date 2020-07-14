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
  return block,inst,cfg


def get_dac_m(dev):
  block = dev.get_block('dac')
  inst = devlib.Location([0,1,2,0])
  cfg = adplib.BlockConfig.make(block,inst)
  cfg.modes = [block.modes.get(['const','m'])]
  cfg['nmos'].value = 7
  cfg['pmos'].value = 3
  cfg['gain_cal'].value = 63
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

  return block,inst,cfg

def get_mult_mh(dev):
  block = dev.get_block('mult')
  inst = devlib.Location([0,1,2,0])
  cfg = adplib.BlockConfig.make(block,inst)
  #cfg.modes = [['+','+','-','m']]
  cfg.modes = [block.modes.get(['x','m','h'])]

  return block,inst,cfg


def get_block(dev):
  #return get_mult_mm(dev)
  return get_dac_h(dev)

