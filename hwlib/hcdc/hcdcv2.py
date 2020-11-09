import hwlib.device as devlib
import hwlib.hcdc.fanout
import hwlib.hcdc.mult
import hwlib.hcdc.integ
import hwlib.hcdc.adc
import hwlib.hcdc.ext_out
import hwlib.hcdc.ext_in
import hwlib.hcdc.lut
import hwlib.hcdc.dac
import hwlib.hcdc.routeblocks as routeblocks
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
    hcdcv2.add_block(hwlib.hcdc.routeblocks.tin)
    hcdcv2.add_block(hwlib.hcdc.routeblocks.tout)
    hcdcv2.add_block(hwlib.hcdc.routeblocks.cin)
    hcdcv2.add_block(hwlib.hcdc.routeblocks.cout)
    hcdcv2.add_block(hwlib.hcdc.ext_in.ext_in)

    # hwtime/wall clock time
    hcdcv2.time_constant = 1.0/126000
    # profiling operations
    hcdcv2.profile_status_type = llenums.ProfileStatus
    hcdcv2.profile_op_type = llenums.ProfileOpType
    if layout:
        hcdc_layout.make(hcdcv2)

    hcdcv2.set_external_pin(llenums.ExternalPins.OUT0, \
                            hwlib.hcdc.ext_out.ext_out, \
                            devlib.Location([0,3,2,0]), \
                            'z', \
                            llenums.Channels.POS)

    hcdcv2.set_external_pin(llenums.ExternalPins.OUT1, \
                            hwlib.hcdc.ext_out.ext_out, \
                            devlib.Location([0,3,2,0]), \
                            'z', \
                            llenums.Channels.NEG)
    


    return hcdcv2
