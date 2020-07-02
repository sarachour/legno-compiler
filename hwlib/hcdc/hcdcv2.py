import hwlib.device as devlib
import hwlib.hcdc.fanout
import hwlib.hcdc.mult
import hwlib.hcdc.integ
import hwlib.hcdc.adc
import hwlib.hcdc.ext_out
import hwlib.hcdc.lut
import hwlib.hcdc.dac
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.layout as hcdc_layout

def get_device(layout=False):
    hcdcv2 = devlib.Device()
    hcdcv2.add_block(hwlib.hcdc.fanout.fan)
    hcdcv2.add_block(hwlib.hcdc.mult.mult)
    hcdcv2.add_block(hwlib.hcdc.integ.integ)
    hcdcv2.add_block(hwlib.hcdc.ext_out.ext_out)
    hcdcv2.add_block(hwlib.hcdc.dac.dac)
    hcdcv2.add_block(hwlib.hcdc.adc.adc)
    hcdcv2.add_block(hwlib.hcdc.lut.lut)

    # profiling operations
    hcdcv2.profile_status_type = llenums.ProfileStatus
    hcdcv2.profile_op_type = llenums.ProfileOpType
    if layout:
        hcdc_layout.make(hcdcv2)

    return hcdcv2
