import sys
import logging
import argparse
import struct
import datetime
from enum import Enum
from lab_bench.devices.sicp_device import SICPDevice
import lab_bench.lib.util as util

logging.basicConfig()

logger = logging.getLogger('osc')
logger.setLevel(logging.INFO)


def extract_number_and_unit(st):
    for i,c in enumerate(st):
        if not c.isdigit() and \
                not c == '.' and \
                not c == 'E' and\
                not c == '-':
            break
    number = float(st[:i])
    unit = st[i:]
    return number,unit


# use python 2
def pairwise(arr):
    for idx in range(0,len(arr)-1,2):
        yield arr[idx],arr[idx+1]

class HoldType(Enum):
        TIME = "TI"
        OFF = "OFF"
        PULSE_SMALLER = "PS"
        PULSE_LARGER = "PL"
        PULSE_IN_RANGE = "P2"
        PULSE_OUT_OF_RANGE = "P1"
        INTERVAL_SMALLER = "IS"
        INTERVAL_LARGER = "IL"
        INTERVAL_IN_RANGE = "I2"
        INTERVAL_OUT_OF_RANGE = "I1"

class HoldRule:

    def __init__(self,hold_type,value1,value2=None):
            self._hold_type = hold_type
            self._value1 = value1
            self._value2 = value2

    def to_cmd(self):
        cmd = "HT,%s,HV,%sS" % (self._hold_type.value,self._value1)
        if not self._value2 is None:
            cmd += ",HV2,%sS" % self._value2
        return cmd

    @staticmethod
    def build(holdtype,value1,value2):
        if holdtype == HoldType.TIME:
            return HRTime(value1)
        elif holdtype == HoldType.OFF:
           return HROff()
        else:
            raise Exception("unhandled: %s" % holdtype)

class HRTime(HoldRule):

    def __init__(self,value):
        HoldRule.__init__(self,HoldType.TIME,value,None)
        self._time = value

    def __repr__(self):
        return "t>%s" % self._time


class HROff(HoldRule):

    def __init__(self):
        HoldRule.__init__(self,HoldType.OFF,0.0,None)
        pass

    def __repr__(self):
        return "off"

class TriggerType(Enum):
    EDGE = "EDGE"

class TriggerSlopeType(Enum):
    FALLING_EDGE = "NEG"
    RISING_EDGE = "POS"
    ALTERNATING_EDGES = "WINDOW"

class Trigger:
    def __init__(self,trigger_type,source,hold_rule,
                 min_voltage=None,
                 which_edge=None):
        self.trigger_type = trigger_type
        self.source = source
        self.when = hold_rule
        self.min_voltage = min_voltage
        self.which_edge = which_edge

    def to_cmds(self):
        yield "TRSE %s,SR,%s,%s" % \
            (self.trigger_type.value,
             self.source.value,
             self.when.to_cmd())

        if not self.which_edge is None:
            yield "TRSL %s" % self.which_edge.value

        if not self.min_voltage is None:
            yield "%s:TRLV %s" % \
                (self.source.value,
                 self.min_voltage)

    @staticmethod
    def build(args):
        scaling = {'ms':1e-3,'s':1.0}
        trigger_type = TriggerType(args[0])
        props = dict(pairwise(args[1:]))
        # TI:time (OFF or TI)
        # HT:hold type
        # HV:hold value
        # SR:source
        chan = Sigilent1020XEOscilloscope.Channels(props['SR'])
        ht = HoldType(props['HT'])
        if 'HV' in props:
            hv,unit = extract_number_and_unit(props['HV'])
            value = float(hv)*1e-3*scaling[unit]
        else:
            value = None

        if 'HV2' in props:
            hv2,unit2 = extract_number_and_unit(props['HV2'])
            value2 = float(hv2)*1e-3*scaling[unit2]
        else:
            value2 = None

        hold_rule = HoldRule.build(ht,value,value2)
        return Trigger(trigger_type,chan,hold_rule)

    def __repr__(self):
        return "trigger[%s](%s) when=%s which_edge=%s min-volt=%s" % \
            (self.trigger_type.name,
             self.source,
             self.when,
             self.which_edge,
             self.min_voltage)


class TriggerModeType(Enum):
    AUTO = "AUTO";
    NORM = "NORM";
    SINGLE = "SINGLE";
    STOP = "STOP"

class Sigilent1020XEOscilloscope(SICPDevice):
    class Channels(Enum):
        ACHAN1 = "C1"
        ACHAN2 = "C2"
        EXT = "EX"
        EXT5 = "EX5"
        LINE = "LINE"

    class OscStatus(Enum):
        READY = "Ready";
        TRIGGERED = "Trig'd";
        STOP = "Stop";
        AUTO = "Auto";
        ARM = "Arm";
        ROLL = "Roll";


    def __init__(self,ipaddr,port):
        SICPDevice.__init__(self,ipaddr,port)
        self._analog_channels = [
            Sigilent1020XEOscilloscope.Channels.ACHAN1,
            Sigilent1020XEOscilloscope.Channels.ACHAN2,
        ]
        self._digital_channels = [
            Sigilent1020XEOscilloscope.Channels.EXT
        ]
        self._channels = self._analog_channels + self._digital_channels
        self._prop_cache = None
        self.TIME_DIVISIONS = 14
        self.VALUE_DIVISIONS = 8

    def flush_cache(self):
        self._prop_cache = None

    def analog_channel(self,idx):
        if idx == 0:
            return Sigilent1020XEOscilloscope.Channels.ACHAN1
        elif idx == 1:
            return Sigilent1020XEOscilloscope.Channels.ACHAN2

        else:
            raise Exception("unknown analog channel.")

    def get_trigger(self):
        cmd = "TRSE?"
        result = self.query(cmd)
        if ">>" in result:
            result = result.split(">>")[-1].strip()

        tokens = result.split(",")
        trig = Trigger.build(tokens)

        cmd = "%s:TRLV?" % (trig.source.value)
        result = self.query(cmd)
        trig.min_voltage = float(result.strip())

        cmd = "%s:TRSL?" % (trig.source.value)
        result = self.query(cmd)
        trig.which_edge = TriggerSlopeType(result.strip())
        return trig

    def get_trigger_mode(self):
        cmd = "TRMD?"
        result = self.query(cmd)
        status = TriggerModeType(result.strip())
        return status

    def set_trigger_mode(self,mode):
        cmd = "TRMD %s" % mode.value
        self.write(cmd)

    def get_history_frame_time(self):
        cmd = "FTIM?"
        resp = self.query(cmd,decode=None)
        # hour: 8 bits
        # minute: 8 bits
        # second: 8 bits
        # microsecond: 48 bits
        # total :64 bits
        hour = int(resp[1])
        minute = int(resp[2])
        second = int(resp[3]) % 100
        bytarr = resp[4:]
        pad = bytearray([0]*(4-len(bytarr)))
        microsec = struct.unpack("<L", pad+bytarr)[0]
        print("%s:%s:%s.%s" % (hour,minute,second,microsec))
        total_seconds = hour*60*60 + minute*60 + second + microsec*10e-6
        if total_seconds == 0:
            return None
        return total_seconds

    def get_history_frame(self):
        cmd = "FRAM?"
        resp = self.query(cmd)
        return int(resp)

    def set_history_frame(self,idx):
        cmd = "FRAM %d" % idx
        self.write(cmd)

    def set_trigger(self,trigger):
        assert(isinstance(trigger,Trigger))
        for cmd in trigger.to_cmds():
            result = self.write(cmd)
        return

    def set_history_mode(self,enable):
        cmd = "HSMD %s" % ("ON" if enable else "OFF")
        self.write(cmd)

    def get_history_mode(self):
        cmd = "HSMD?"
        result = self.query(cmd)
        if result == "ON":
            return True
        elif result == "OFF":
            return False
        else:
            raise Exception("unexpected response <%s>" % result)

    def ext_channel(self):
        return Sigilent1020XEOscilloscope.Channels.EXT

    def setup(self):
        SICPDevice.setup(self)
        if self.ready():
            self.write("CHDR OFF")


    def _validate(self,cmd,result):
        args = result.strip().split()
        return args

    def set_trigger_level(self,amt):
        cmd = "TRLV %fV" % amt
        self.write(cmd)


    def get_trigger_level(self):
        cmd = "TRLV?"
        result = self.query(cmd)
        return float(result)


    def get_trigger_delay(self):
        cmd = "TRDL?"
        result = self.query(cmd)
        return float(result)

    def get_sample_status(self):
        cmd = "SAST?"
        result = self.query(cmd)
        args = self._validate("SAST",result)
        status = Sigilent1020XEOscilloscope.OscStatus(args[0])
        if status is None:
            raise Exception("unknown status <%s>" % args[0])
        return status

    def get_n_samples(self,channel):
        assert(channel in self._channels)
        cmd = 'SANU? %s' % channel.value
        result = self.query(cmd)
        args = self._validate("SANU",result)
        npts,unit = extract_number_and_unit(args[0])
        if unit == 'Mpts':
            return int(npts)*1e6
        elif unit == 'kpts':
            return int(npts)*1e3
        elif unit  == "pts":
            return int(npts)
        else:
            raise Exception("<%s> unknown unit <%s>" % \
                    (args[0],unit))


    def set_trigger_delay(self,time_s):
        if time_s >= 1.0 or time_s == 0:
            time = time_s
            unit = "S"
        elif time_s >= 1.0e-3:
            time = time_s*1.0e3
            unit = "MS"
        elif time_s > 1e-6:
            time = time_s*1.0e6
            unit = "US"
        elif time_s > 1e-9:
            time = time_s*1.0e9
            unit = "NS"
        else:
            raise Exception("time <%s> unsupportd" % time_s)

        cmd = "TRDL %s%s" % (time,unit)
        self.write(cmd)
        self.flush_cache()

    def closest_seconds_per_division(self,time_s,round_mode=util.RoundMode.UP):
        times = []
        for scale in [1e-9,1e-6,1e-3]:
            for val in [1,2,5,10,20,50,100,200,500]:
                times.append(val*scale)

        for val in [1,2,5,10,20,50,100]:
            times.append(val)

        _,time_s = util.find_closest(times,time_s,round_mode)
        return time_s

    def set_seconds_per_division(self,time_s,round_mode=util.RoundMode.UP):
        time_s = self.closest_seconds_per_division(time_s,round_mode)
        unit = None
        if time_s >= 1.0:
            time = time_s
            unit = "S"
        elif time_s >= 1.0e-3:
            time = time_s*1.0e3
            unit = "MS"
        elif time_s > 1e-6:
            time = time_s*1.0e6
            unit = "US"
        elif time_s > 1e-9:
            time = time_s*1.0e9
            unit = "NS"

        cmd = "TDIV %s%s" % (time,unit)
        self.write(cmd)
        self.flush_cache()
        return time_s

    def get_memory_size(self):
        cmd = "MSIZ?"
        resp = self.query(cmd)
        value,unit = extract_number_and_unit(resp)
        if unit == "K":
            return value*1000
        elif unit == "M":
            return value*10e6

    def set_memory_size(self,amt_kb,round_mode=util.RoundMode.UP):
        unit = None
        if amt_kb > 1e3:
            amt = amt_kb/1.0e3
            unit = "M"
        else:
            amt = amt_kb
            unit = "K"

        sizes = {}
        sizes['K'] = [7,14,70,140,700]
        sizes['M'] = [1.4,7,14]
        _,amt = util.find_closest(sizes[unit],amt,round_mode)
        cmd = "MSIZ %s" % amt
        self.flush_cache()
        self.write(cmd)

    def get_sample_rate(self):
        cmd = 'SARA?'
        result = self.query(cmd)
        args = self._validate("SARA",result)
        rate,unit = extract_number_and_unit(args[0])
        if unit == 'Sa/s':
            return rate
        elif unit == "kSa/s":
            return rate*1e3
        elif unit == "GSa/s":
            return rate*1e9
        elif unit == "MSa/s":
            return rate*1e6
        else:
            raise Exception("unknown unit <%s>" % unit)

    def set_volts_per_division(self,channel,volts_per_div):
        assert(channel in self._channels)
        cmd = '%s:VDIV %fV' % (channel.value,volts_per_div)
        self.flush_cache()
        self.write(cmd)

    def set_voltage_offset(self,channel,volts_offset):
        assert(channel in self._channels)
        cmd = "%s:OFST %fV" % (channel.value,volts_offset)
        self.flush_cache()
        self.write(cmd)
    # ge
    def get_volts_per_division(self,channel):
        assert(channel in self._channels)
        cmd = '%s:VDIV?' % channel.value
        result = self.query(cmd)
        args = self._validate("VDIV",result)
        tc = float(args[0])
        return tc

    # get time constant
    def get_seconds_per_division(self):
        cmd = 'TDIV?'
        result = self.query(cmd)
        # seconds per division.
        args = self._validate("TDIV",result)
        tc = float(args[0])
        return tc


    def set_waveform_params(self,n_pts,start=0,stride=0,
                            all_points_in_memory=False):
        cmd = "WFSU SP,%d,NP,%d,FP,%d" % (stride,n_pts,start)
        result = self.write(cmd)
        cmd = "WFSU TYPE,%d" % (0 if not all_points_in_memory else 1)
        result = self.write(cmd)

    def get_voltage_offset(self,channel):
        assert(channel in self._channels)
        cmd = "%s:OFST?" % channel.value
        result = self.query(cmd)
        args = self._validate("OFST",result)
        off = float(args[0])
        return off

    def get_waveform_params(self):
        cmd = "WFSU?"
        result = self._dev.query(cmd)
        return result

    def get_waveform_format(self):
        cmd = "TEMPLATE?"
        self._dev.write(cmd)
        result = self._dev.read_raw()
        return result

    def get_properties(self):
        if not self._prop_cache is None:
            return self._prop_cache
        ident = self.get_identifier()
        msiz = self.get_memory_size()
        status = self.get_sample_status()
        rate = self.get_sample_rate()
        sec_per_div = self.get_seconds_per_division()
        trig_delay = self.get_trigger_delay()
        channels = self._channels
        samples = {}
        volt_scale = {}
        offset = {}
        for channel in self._analog_channels:
            samples[channel.name] = self.get_n_samples(channel)
            volt_scale[channel.name] = self.get_volts_per_division(channel)
            offset[channel.name] = self.get_voltage_offset(channel)

        self._prop_cache = {
            'identifier': ident,
            'status': status,
            'trig_delay': trig_delay,
            'sampling_rate': rate,
            'memory_bytes': msiz,
            'seconds_per_division':sec_per_div,
            'channels':channels,
            'n_samples':samples,
            'volts_per_division':volt_scale,
            'voltage_offset':offset
        }
        return self._prop_cache

    def acquire(self):
        resp = self.query("INR?")
        print(resp)
        resp = self.query("INR?")
        print(resp)
        self.write("ARM")

    def stop(self):
        self.write("STOP")


    def auto(self):
        self.write("AUTO")

    def set_history_list_open(self,v):
        cmd = "HSLST %s" % ("ON" if v else "OFF")
        self.write(cmd)

    def is_history_list_open(self):
        cmd = "HSLST?"
        resp = self.query(cmd)
        return True if "ON" in resp else False

    def waveform(self,channel):
        assert(channel in self._channels)
        props = self.get_properties()
        #NHDIV = 14
        #NVDIV = 8
        NHDIV = 14
        NVDIV=25
        tdiv = props['seconds_per_division']
        sara = props['sampling_rate']
        vdiv = props['volts_per_division'][channel.name]
        voff = props['voltage_offset'][channel.name]

        cmd = "%s:WF? DAT2" % channel.value
        resp = self.query(cmd,decode=None,timeout_sec=180)
        code_idx = None
        for idx,byte in enumerate(resp):
            chrs = chr(byte)
            if len(resp) < idx+2:
                raise Exception("message too small %s" % resp)
            chrs += chr(resp[idx+1])
            if chrs == '#9':
                code_idx = idx
                break

        if(code_idx is None):
            raise Exception("could not find marker")

        idx_start = code_idx+2+9
        data_size = int(resp[idx+2:idx_start])
        data_ba = resp[idx_start:idx_start+data_size]

        times = []
        volts = []
        for idx,value in enumerate(data_ba):
            if value > 127:
                value -= 255

            volt = value/NVDIV*vdiv-voff
            time = -tdiv*NHDIV/2.0+idx*(1.0/sara)
            volts.append(volt)
            times.append(time)


        return list(times),list(volts)


    def full_waveform(self,channel):
        curr_frame = 1
        start_time = None
        done = False
        abs_times = []
        abs_values = []
        self.set_history_mode(True)
        self.set_history_list_open(True)
        assert(self.is_history_list_open())
        print("-> build frames")
        dataframes = []
        while not done:
            self.set_history_frame(curr_frame)
            read_frame = self.get_history_frame()
            if read_frame != curr_frame:
                done = True
                continue

            curr_time = self.get_history_frame_time()
            if start_time is None:
                start_time = curr_time

            assert(not curr_time is None)
            delta = curr_time - start_time
            times,values = self.waveform(channel)
            dataframes.append((curr_frame,delta,times,values))
            curr_frame += 1

        self.set_history_list_open(False)
        print("-> build data")
        times = []
        values = []
        for frame_idx,delta,dfr_times,dfr_values in dataframes:
            min_time = min(dfr_times)
            offset = delta + abs(min_time)
            times += list(map(lambda time: time + offset, dfr_times))
            values += dfr_values

        print("-> returning data")
        return times,values

    def screendump(self,filename):
        cmd = "SCDP"
        result = self.query(cmd)
        with open(filename,'wb') as fh:
            fh.write(result)
