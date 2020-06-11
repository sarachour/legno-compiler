import hwlib.device as devlib
import hwlib.hcdc.fanout
import hwlib.hcdc.mult
import hwlib.hcdc.integ
import hwlib.hcdc.adc
import hwlib.hcdc.ext_out
import hwlib.hcdc.dac

def get_device(layout=False):
    hcdcv2 = devlib.Device()
    hcdcv2.add_block(hwlib.hcdc.fanout.fan)
    hcdcv2.add_block(hwlib.hcdc.mult.mult)
    hcdcv2.add_block(hwlib.hcdc.integ.integ)
    hcdcv2.add_block(hwlib.hcdc.ext_out.ext_out)
    hcdcv2.add_block(hwlib.hcdc.dac.dac)
    hcdcv2.add_block(hwlib.hcdc.adc.adc)
    return hcdcv2
