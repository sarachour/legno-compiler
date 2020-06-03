import hwlib2.device as devlib
import hwlib2.hcdc.fanout
import hwlib2.hcdc.mult
import hwlib2.hcdc.adc

def get_device(layout=False):
    hcdcv2 = devlib.Device()
    hcdcv2.add_block(hwlib2.hcdc.fanout.fan)
    hcdcv2.add_block(hwlib2.hcdc.mult.mult)
    hcdcv2.add_block(hwlib2.hcdc.dac.dac)
    hcdcv2.add_block(hwlib2.hcdc.adc.adc)
    return hcdcv2
