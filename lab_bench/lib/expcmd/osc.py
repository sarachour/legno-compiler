from lab_bench.lib.base_command import Command
import lab_bench.devices.sigilent_osc as osclib
from lab_bench.lib.expcmd.common import *
import numpy as np
import util.util as util

class OscSetVoltageRangeCmd(Command):

    def __init__(self,chan_id,low,high):
        Command.__init__(self)
        self._chan_id = chan_id
        self._low = low
        self._high = high

    @staticmethod
    def name():
        return 'osc_set_volt_range'


    @staticmethod
    def desc():
        return "[oscilloscope] set the ranges of the voltages read from the oscilloscope."


    def __repr__(self):
        return "%s %d %f %f" % (self.name(),self._chan_id,
                                self._low,self._high)


    @staticmethod
    def parse(args):
        return strict_do_parse("{chan_id:d} {low:g} {high:g}", \
                        args, \
                        OscSetVoltageRangeCmd)


    def execute(self,state):
        if state.dummy:
            return

        vdivs = state.oscilloscope.VALUE_DIVISIONS
        chan = state.oscilloscope.analog_channel(self._chan_id)
        volt_offset = -(self._low+self._high)/2.0
        volts_per_div = (self._high-self._low)/vdivs
        state.oscilloscope \
             .set_volts_per_division(chan,volts_per_div)
        state.oscilloscope \
            .set_voltage_offset(chan,volt_offset)


class OscGetValuesCmd(Command):

    def __init__(self,filename,variable,chan_low,chan_high=None):
        Command.__init__(self)
        self._filename = filename
        self._differential = False if chan_high is None else True
        self._chan_low = chan_low
        self._chan_high = chan_high
        self._variable = variable

    @property
    def filename(self):
        return self._filename

    @staticmethod
    def name():
        return 'osc_get_values'


    @staticmethod
    def desc():
        return "[oscilloscope] get the values read from an oscilloscope."


    @staticmethod
    def parse(args):
        line = " ".join(args)
        types = ['differential','direct']
        cmd1 = "differential {chan_low:d} {chan_high:d} {variable} {filename}"
        opt_result1 = do_parse(cmd1, args, OscGetValuesCmd)
        if opt_result1.success:
            return opt_result1.value

        cmd2 = "direct {chan_low:d} {variable} {filename}"
        opt_result2 = do_parse(cmd2,args,OscGetValuesCmd)
        if opt_result2.success:
            return opt_result2.value

        raise Exception(opt_result1.message + "\nOR\n" +
                        opt_result2.message)

    def process_data(self,state,filename,variable,chan1,chan2):
        # compute differential or direct
        #pos channel
        #y = 1.0115x - 13.872
        #R² = 0.99999
        mV = 1.0/1000.0
        CHAN1_SLOPE = 1.0115
        CHAN1_OFFSET = -13.72*mV
        #neg channel
        #y = 1.0151x - 11.135
        #R² = 0.99981
        CHAN2_SLOPE = 1.0151
        CHAN2_OFFSET = -11.135*mV

        if self._differential:
            out_t1,out_v1 = chan1
            out_t2,out_v2 = chan2
            def compute(i):
                v1 = out_v1[i]*CHAN1_SLOPE+CHAN1_OFFSET
                v2 = out_v2[i]*CHAN2_SLOPE+CHAN2_OFFSET
                return v1-v2

            n = len(out_v1)
            out_v = list(map(lambda i: compute(i), range(n)))
            assert(all(np.equal(out_t1,out_t2)))
            out_t = out_t1

        else:
            out_t,out_v = chan1
            def compute(i):
                v1 = out_v[i]*CHAN1_SLOPE+CHAN1_OFFSET
                return v

            out_v = list(map(lambda i: compute(i), range(n)))

        theo_time_per_div = float(state.sim_time) / state.oscilloscope.TIME_DIVISIONS
        act_time_per_div = state.oscilloscope\
                                .closest_seconds_per_division(theo_time_per_div)
        # the oscilloscope leaves two divisions of buffer room for whatever reason.
        print("<writing file>")
        with open(filename,'w') as fh:
            obj = {'times':list(out_t),
                   'values': list(out_v),
                   'variable':variable}
            print("-> compressing data")
            strdata = util.compress_json(obj)
            fh.write(strdata)
        print("<wrote file>")


    def execute(self,state):
        if not state.dummy:
            props = state.oscilloscope.get_properties()
            chan = state.oscilloscope.analog_channel(self._chan_low)


            #ch1 = state.oscilloscope.full_waveform(chan)
            ch1 = state.oscilloscope.waveform(chan)

            ch2 = None
            if self._differential:
                chan = state.oscilloscope.analog_channel(self._chan_high)
                #ch2 = state.oscilloscope.full_waveform(chan)
                ch2 = state.oscilloscope.waveform(chan)

            return self.process_data(state,self._filename, \
                                     self._variable,
                                     ch1,ch2)


    def __repr__(self):
        if not self._differential:
            return "%s direct %d %s %s" % (self.name(),
                                        self._chan_low,
                                        self._variable,
                                        self._filename)
        else:
            return "%s differential %d %d %s %s" % (self.name(),
                                        self._chan_low,
                                        self._chan_high,
                                        self._variable,
                                        self._filename)



class OscSetSimTimeCmd(Command):

    def __init__(self,sim_time,frame_time=None):
        Command.__init__(self)
        self._sim_time = sim_time
        self._frame_time = (sim_time if frame_time is None else frame_time)

    @staticmethod
    def name():
        return 'osc_set_sim_time'

    def __repr__(self):
        return "%s %.3e" % (self.name(),self._sim_time)


    @staticmethod
    def parse(args):
        return strict_do_parse("{sim_time:g}", args, \
                               OscSetSimTimeCmd)


    def configure_oscilloscope(self,state,_time_sec,slack=0.00, \
                               extend=1.0e-4):
        slack_sec = _time_sec*slack+extend
        frame_sec = _time_sec+slack_sec
        time_sec = _time_sec+slack_sec
        # TODO: multiple segments of high sample rate.
        theo_time_per_div = float(time_sec) / state.oscilloscope.TIME_DIVISIONS
        act_time_per_div = state.oscilloscope \
                                .closest_seconds_per_division(theo_time_per_div)
        trig_delay = act_time_per_div * (float(state.oscilloscope.TIME_DIVISIONS/2.0))
        print("desired sec/div %s" % theo_time_per_div)
        print("actual sec/div %s" % act_time_per_div)
        print("sec: %s" % time_sec)
        print("delay: %s" % trig_delay)
        state.oscilloscope.set_seconds_per_division(theo_time_per_div)
        state.oscilloscope.set_trigger_delay(trig_delay)
        return frame_sec

    def execute(self,state):
        if not state.dummy:
            frame_time_sec = self.configure_oscilloscope(state,self._sim_time)
            self._frame_time = frame_time_sec

    @staticmethod
    def desc():
        return "set the number of samples to record (max 10000)"


    @staticmethod
    def desc():
        return "[oscilloscope] set the simulation time and input time"


class OscSetupTrigger(Command):

    def __init__(self):
        Command.__init__(self)

    @staticmethod
    def name():
        return 'osc_setup_trigger'

    @staticmethod
    def desc():
        return "[oscilloscope] setup edge trigger on oscilloscope."



    @staticmethod
    def parse(args):
        return strict_do_parse("",args,OscSetupTrigger)


    def exec_setup_osc(self,state):
        if state.use_osc and not state.dummy:
            # osclib.HRTime(80e-7)
            edge_trigger = osclib.Trigger(osclib.TriggerType.EDGE,
                                state.oscilloscope.ext_channel(),
                                osclib.HROff(),
                                min_voltage=0.080,
                                which_edge=osclib
                                          .TriggerSlopeType
                                          .ALTERNATING_EDGES)
            state.oscilloscope.set_trigger(edge_trigger)
            state.oscilloscope.set_trigger_mode(osclib.TriggerModeType.NORM)

            trig = state.oscilloscope.get_trigger()
            print("trigger: %s" % trig)
            #state.oscilloscope.set_history_mode(True)
            props = state.oscilloscope.get_properties()
            print("== oscilloscope properties")
            for key,val in props.items():
                print("%s : %s" % (key,val))


    def __repr__(self):
        return self.name()


    def execute(self,state):
        self.exec_setup_osc(state)

