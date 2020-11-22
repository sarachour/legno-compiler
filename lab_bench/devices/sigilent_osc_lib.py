import lab_bench.devices.sigilent_osc as osclib
import numpy as np

def set_voltage_range(osc,chan_id,ival):
        vdivs = osc.VALUE_DIVISIONS
        chan = osc.analog_channel(chan_id)
        volt_offset = -(ival.lower+ival.upper)/2.0
        volts_per_div = (ival.upper-ival.lower)/vdivs
        osc.set_volts_per_division(chan,volts_per_div)
        osc.set_voltage_offset(chan,volt_offset)



def get_waveform(osc,chan1,chan2,differential=True):
        # compute differential or direct
        #pos channel
        #y = 1.0115x - 13.872
        #R² = 0.99999
        if chan2 is None and differential:
            raise Exception("channel 2 is unset but differential mode is selected")
            differential = False

        mV = 1.0/1000.0
        CHAN1_SLOPE = 1.0115
        CHAN1_OFFSET = -13.72*mV
        #neg channel
        #y = 1.0151x - 11.135
        #R² = 0.99981
        CHAN2_SLOPE = 1.0151
        CHAN2_OFFSET = -11.135*mV
        data1 = osc.waveform(chan1)
        data2 = None
        if differential:
            data2 = osc.waveform(chan2)


        if differential:
            out_t1,out_v1 = data1
            out_t2,out_v2 = data2
            def compute(i):
                v1 = out_v1[i]*CHAN1_SLOPE+CHAN1_OFFSET
                v2 = out_v2[i]*CHAN2_SLOPE+CHAN2_OFFSET
                return v1-v2

            n = len(out_v1)
            out_v = list(map(lambda i: compute(i), range(n)))
            assert(all(np.equal(out_t1,out_t2)))
            out_t = out_t1

        else:
            out_t,out_v = data1
            def compute(i):
                v1 = out_v[i]*CHAN1_SLOPE+CHAN1_OFFSET
                return v

            out_v = list(map(lambda i: compute(i), range(n)))

        return list(out_t),list(out_v)


def set_trigger(osc):
    # osclib.HRTime(80e-7)
    edge_trigger = osclib.Trigger(osclib.TriggerType.EDGE,
                                  osc.ext_channel(),
                                  osclib.HROff(),
                                  min_voltage=0.080,
                                  which_edge=osclib
                                        .TriggerSlopeType
                                        .ALTERNATING_EDGES)
    osc.set_trigger(edge_trigger)
    osc.set_trigger_mode(osclib.TriggerModeType.NORM)

    trig = osc.get_trigger()
    print("trigger: %s" % trig)
    #state.oscilloscope.set_history_mode(True)
    props = osc.get_properties()
    print("== oscilloscope properties")
    for key,val in props.items():
        print("%s : %s" % (key,val))



def set_time(osc,hwtime_sec,slack=0.00, \
                           extend=1.0e-4):
        slack_sec = hwtime_sec*slack+extend
        frame_sec = hwtime_sec+slack_sec
        time_sec = hwtime_sec+slack_sec
        # TODO: multiple segments of high sample rate.
        theo_time_per_div = float(time_sec) / osc.TIME_DIVISIONS
        act_time_per_div = osc.closest_seconds_per_division(theo_time_per_div)
        trig_delay = act_time_per_div * (float(osc.TIME_DIVISIONS/2.0))
        print("desired sec/div %s" % theo_time_per_div)
        print("actual sec/div %s" % act_time_per_div)
        print("sec: %s" % time_sec)
        print("delay: %s" % trig_delay)
        osc.set_seconds_per_division(theo_time_per_div)
        osc.set_trigger_delay(trig_delay)
        return frame_sec

