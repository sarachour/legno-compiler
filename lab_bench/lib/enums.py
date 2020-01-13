from enum import Enum

class PortType(Enum):
    PORT_INPUT = 'input';
    PORT_OUTPUT= 'output';

    def code(self):
        if self == PortType.PORT_INPUT:
            return 0
        else:
            return 1

class PortName(str,Enum):
    IN0 = "in0"
    IN1 = "in1"
    OUT0 = "out0"
    OUT1 = "out1"
    OUT2 = "out2"

    def code(self):
        data = {
            PortName.IN0:0,
            PortName.IN1:1,
            PortName.OUT0:2,
            PortName.OUT1:3,
            PortName.OUT2:4,
        }
        return data[self]

    @staticmethod
    def from_code(v):
        data = [PortName.IN0, PortName.IN1, PortName.OUT0,
                PortName.OUT1, PortName.OUT2]
        return data[int(v)]

    def __lt__(self,other):
        return str(self) < str(other)

class BlockType(str,Enum):
    DAC = 'dac';
    ADC = 'adc';
    CHIP_INPUT = 'chip_input';
    CHIP_OUTPUT = 'chip_output';
    TILE_INPUT = "tile_input";
    TILE_OUTPUT = "tile_output";
    MULT = "mult";
    INTEG = "integ";
    FANOUT = "fanout";
    LUT = "lut";
    NONE = "<none>";

    def code(self):
        mapping = {
            BlockType.DAC: 0,
            BlockType.MULT: 5,
            BlockType.INTEG: 6,
            BlockType.FANOUT: 7,
            BlockType.LUT: 8,
            BlockType.ADC: 9
        }
        return mapping[self]


class CircCmdType(Enum):
    USE_DAC = 'use_dac';
    USE_MULT = 'use_mult';
    USE_FANOUT = 'use_fanout';
    USE_INTEG = 'use_integ';
    USE_LUT = 'use_lut';
    USE_ADC = 'use_adc';
    DISABLE_DAC = 'disable_dac';
    DISABLE_MULT = 'disable_mult';
    DISABLE_INTEG = 'disable_integ';
    DISABLE_FANOUT = 'disable_fanout';
    DISABLE_LUT = 'disable_lut';
    DISABLE_ADC = 'disable_adc';
    CONNECT = 'connect';
    BREAK = 'break';
    CALIBRATE = 'calibrate';
    GET_INTEG_STATUS = 'get_integ_status';
    GET_ADC_STATUS = 'get_adc_status';
    WRITE_LUT = "write_lut";
    GET_STATE = "get_state";
    SET_STATE = "set_state";
    MEASURE = "measure";
    TUNE = "tune";
    DEFAULTS = "defaults";
    PROFILE = "profile";

class ExpCmdType(Enum):
    RESET = 'reset';
    USE_ANALOG_CHIP = 'use_analog_chip';
    SET_SIM_TIME= 'set_sim_time';
    USE_OSC = 'use_osc';
    RUN = 'run';

class CmdType(Enum):
    CIRC_CMD = 'circ_cmd';
    EXPERIMENT_CMD = 'exp_cmd';
    FLUSH_CMD = 'flush_cmd';
