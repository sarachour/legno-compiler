import hwlib2.device as devlib
import hwlib2.hcdc.fanout

def get_device(layout=False):
    hcdcv2 = devlib.Device()
    hcdcv2.add_block(hwlib2.hcdc.fanout.fan)
    return hcdcv2
