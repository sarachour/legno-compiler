import hwlib2.hcdc.fanout
import hwlib2.hcdc.lut
import hwlib2.hcdc.dac
import hwlib2.hcdc.adc
import hwlib2.hcdc.mult
import hwlib2.hcdc.integ

import hwlib2.device as devlib
import hwlib2.adp as adplib
import hwlib2.hcdc.llstructs as llstructs
import hwlib2.hcdc.llenums as llenums
import hwlib2.hcdc.llcmd as llcmd

from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum

'''
The following functions turn a configured block
into a set_state command.
'''

def test_fanout():
  loc = devlib.Location([0,3,2,0])
  blk = hwlib2.hcdc.fanout.fan

  cfg = adplib.ADP()
  cfg.add_instance(blk,loc)
  blkcfg = cfg.configs.get(blk.name,loc)
  blkcfg.modes = [['+','+','-','m']]

  runtime = GrendelRunner()
  runtime.initialize()

  #llcmd.set_state(runtime,blk,loc,cfg)

  result = llcmd.profile(runtime,blk,loc,cfg, \
                        output_port=llenums.PortType.OUT2, \
                        in0=1.2)
  print(result)
  runtime.close()

def test_vga():
  loc = devlib.Location([0,3,2,0])
  blk = hwlib2.hcdc.mult.mult

  cfg = adplib.ADP()
  cfg.add_instance(blk,loc)
  blkcfg = cfg.configs.get(blk.name,loc)
  blkcfg.modes = [['x','m','h']]
  blkcfg.data['c'] = 0.5

  runtime = GrendelRunner()
  runtime.initialize()

  result = llcmd.profile(runtime,blk,loc,cfg, \
                        output_port=llenums.PortType.OUT0, \
                        in0=1.2)
  print(result)
  runtime.close()

def test_mult():
  loc = devlib.Location([0,3,2,0])
  blk = hwlib2.hcdc.mult.mult

  cfg = adplib.ADP()
  cfg.add_instance(blk,loc)
  blkcfg = cfg.configs.get(blk.name,loc)
  blkcfg.modes = [['m','m','h']]

  runtime = GrendelRunner()
  runtime.initialize()

  result = llcmd.profile(runtime,blk,loc,cfg, \
                         output_port=llenums.PortType.OUT0, \
                         in0=1.2,
                         in1=1.5)
  print(result)
  runtime.close()


def test_dac():
  loc = devlib.Location([0,3,2,0])
  blk = hwlib2.hcdc.dac.dac

  cfg = adplib.ADP()
  cfg.add_instance(blk,loc)
  blkcfg = cfg.configs.get(blk.name,loc)
  blkcfg.modes = [['const','h']]
  blkcfg['c'].value = 0.5
  blkcfg['c'].scf = 1.0

  runtime = GrendelRunner()
  runtime.initialize()

  result = llcmd.profile(runtime,blk,loc,cfg, \
                         output_port=llenums.PortType.OUT0)
  print(result)
  runtime.close()

def test_adc():
  loc = devlib.Location([0,3,2,0])
  blk = hwlib2.hcdc.adc.adc

  cfg = adplib.ADP()
  cfg.add_instance(blk,loc)
  blkcfg = cfg.configs.get(blk.name,loc)
  blkcfg.modes = [['m']]

  runtime = GrendelRunner()
  runtime.initialize()

  result = llcmd.profile(runtime,blk,loc,cfg, \
                         output_port=llenums.PortType.OUT0, \
                         in0=1.0)
  runtime.close()

def test_integ():
  loc = devlib.Location([0,3,2,0])
  blk = hwlib2.hcdc.integ.integ

  cfg = adplib.ADP()
  cfg.add_instance(blk,loc)
  blkcfg = cfg.configs.get(blk.name,loc)
  blkcfg.modes = [['m','h','+']]
  blkcfg['z0'].value = 0.32

  runtime = GrendelRunner()
  runtime.initialize()

  result = llcmd.profile(runtime,blk,loc,cfg, \
                         method=llenums.ProfileOpType.INTEG_INITIAL_COND.name,
                         output_port=llenums.PortType.OUT0, \
                         in0=1.0)

  runtime.close()


#test_dac()
#test_adc()
test_integ()
