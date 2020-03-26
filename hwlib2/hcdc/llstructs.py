import construct as cstruct
import hwlib2.hcdc.llenums as llenums

def lut_source_t():
    kwargs = {
        llenums.LUTSourceType.ADC0.value:0,
        llenums.LUTSourceType.ADC1.value:1,
        llenums.LUTSourceType.EXTERN.value:2,
        llenums.LUTSourceType.CONTROLLER.value:3
    }
    return cstruct.Enum(cstruct.Int8ul,**kwargs)

def dac_source_t():
    kwargs = {
        llenums.DACSourceType.MEM.value:0,
        llenums.DACSourceType.EXTERN.value:1,
        llenums.DACSourceType.LUT0.value:2,
        llenums.DACSourceType.LUT1.value:3
    }
    return cstruct.Enum(cstruct.Int8ul,**kwargs)

def range_t():
    kwargs = {
        llenums.RangeType.HIGH.value:0,
        llenums.RangeType.MED.value:1,
        llenums.RangeType.LOW.value:2,
        llenums.RangeType.UNKNOWN.value:3
    }
    return cstruct.Enum(cstruct.Int8ul,**kwargs)

def sign_t():
    kwargs = {
        llenums.SignType.POS.value:0,
        llenums.SignType.NEG.value:1
    }
    return cstruct.Enum(cstruct.Int8ul,**kwargs)

def bool_t():
    kwargs = {
        llenums.BoolType.TRUE.value:1,
        llenums.BoolType.FALSE.value:0
    }
    return cstruct.Enum(cstruct.Int8ul,**kwargs)

def block_type_t():
    kwargs = {
        llenums.BlockType.DAC.name:0,
        llenums.BlockType.CHIP_INPUT.name:1,
        llenums.BlockType.CHIP_OUTPUT.name:2,
        llenums.BlockType.TILE_INPUT.name:3,
        llenums.BlockType.TILE_OUTPUT.name:4,
        llenums.BlockType.MULT.name:5,
        llenums.BlockType.INTEG.name:6,
        llenums.BlockType.FANOUT.name:7,
        llenums.BlockType.LUT.name:8,
        llenums.BlockType.ADC.name:9
    }
    return cstruct.Enum(cstruct.Int8ul,**kwargs)

def port_type_t():
    kwargs = {
        llenums.PortType.IN0.name:0,
        llenums.PortType.IN1.name:1,
        llenums.PortType.OUT0.name:2,
        llenums.PortType.OUT1.name:3,
        llenums.PortType.OUT2.name:4
    }
    return cstruct.Enum(cstruct.Int8ul,**kwargs)


def block_loc_t():
    return cstruct.Struct(
        "block" / block_type_t(),
        "chip"/cstruct.Int8ul,
        "tile"/cstruct.Int8ul,
        "slice"/cstruct.Int8ul,
        "idx"/cstruct.Int8ul
    )

def port_loc_t():
    return cstruct.Struct(
        "loc"/block_loc_t(),
        "port"/port_type_t()
    )

# state data
def adc_state_t():
    return cstruct.Struct(
        "test_en" / bool_t(),
        "test_adc" / bool_t(),
        "test_i2v" / bool_t(),
        "test_rs" / bool_t(),
        "test_rsinc" / bool_t(),
        "enable" / bool_t(),
        "pmos" / cstruct.Int8ul,
        "nmos" / cstruct.Int8ul,
        "pmos2" / cstruct.Int8ul,
        "i2v_cal" / cstruct.Int8ul,
        "upper_fs" / cstruct.Int8ul,
        "upper" / cstruct.Int8ul,
        "lower_fs" / cstruct.Int8ul,
        "lower" / cstruct.Int8ul,
        "range" / range_t()
    )

def dac_state_t():
    return cstruct.Struct(
        "enable" / bool_t(),
        "inv" / sign_t(),
        "range" / range_t(),
        "source" / dac_source_t(),
        "pmos" / cstruct.Int8ul,
        "nmos" / cstruct.Int8ul,
        "gain_cal" / cstruct.Int8ul,
        "const_code" / cstruct.Int8ul
    )

def mult_state_t():
    return cstruct.Struct(
        "enable" / bool_t(),
        "vga" / bool_t(),
        "range" / cstruct.Array(3,range_t()),
        "pmos" / cstruct.Int8ul,
        "nmos" / cstruct.Int8ul,
        "port_cal" / cstruct.Array(3,cstruct.Int8ul),
        "gain_cal" / cstruct.Int8ul,
        "gain_code" / cstruct.Int8ul,
        cstruct.Padding(1)
    )

def fanout_state_t():
    return cstruct.Struct(
        "pmos" / cstruct.Int8ul,
        "nmos" / cstruct.Int8ul,
        "range" / range_t(),
        "port_cal" / cstruct.Array(5,range_t()),
        "inv" / cstruct.Array(5,sign_t()),
        "enable" / bool_t(),
        "third" / bool_t()
    )

def lut_state_t():
    return cstruct.Struct(
        "source" / lut_source_t()
    )

def integ_state_t():
    return cstruct.Struct(
        "cal_enable" / cstruct.Array(3,bool_t()),
        "inv" / sign_t(),
        "enable" / bool_t(),
        "exception" / bool_t(),
        # 7 bytes in
        "range" / cstruct.Array(3,range_t()),
        # 10 bytes in
        "pmos" / cstruct.Int8ul,
        "nmos" / cstruct.Int8ul,
        "ic_cal" / cstruct.Int8ul,
        "ic_code" / cstruct.Int8ul,
        # 14 bytes in
        "port_cal" / cstruct.Array(3,cstruct.Int8ul),
        cstruct.Padding(2)

    )


def circ_cmd_type():
    kwargs = {
        llenums.CircCmdType.NULLCMD.name:0,
        llenums.CircCmdType.DISABLE.name:1,
        llenums.CircCmdType.CONNECT.name:2,
        llenums.CircCmdType.BREAK.name:3,
        llenums.CircCmdType.GET_STATUS.name:4,
        llenums.CircCmdType.WRITE_LUT.name:5,
        llenums.CircCmdType.CALIBRATE.name:6,
        llenums.CircCmdType.GET_STATE.name:7,
        llenums.CircCmdType.SET_STATE.name:8,
        llenums.CircCmdType.DEFAULTS.name:9,
        llenums.CircCmdType.PROFILE.name:10
    }
    return cstruct.Enum(cstruct.Int8ul,
                        **kwargs)


# return types
def state_t():
    return cstruct.Union(None,
                         "lut" / lut_state_t(),
                         "dac"/ dac_state_t(),
                         "mult" / mult_state_t(),
                         "integ" / integ_state_t(),
                         "fanout" / fanout_state_t(),
                         "adc" / adc_state_t()
    )

# returned profiling information
def profile_t():
    return cstruct.Struct(
        "spec" / circ_prof_t(),
        "mean" / cstruct.Float32l,
        "stdev" / cstruct.Float32l,
        "error" / cstruct.Float32l
    )

# high-level commmands
def cmd_set_state_t():
    return cstruct.Struct(
        "inst" / block_loc_t(),
        "state" / state_t()
    )

def cmd_connection_t():
    return cstruct.Struct(
        "src" / port_loc_t(),
        "dest" / port_loc_t()
    )

def cmd_profile_t():
    return cstruct.Struct(
        "method" / cstruct.Int8ul,
        cstruct.Padding(1),
        "inst" / block_loc_t(),
        "in_ports" / cstruct.Array(2,cstruct.Int8ul),
        "in_vals" / cstruct.Array(2,cstruct.Float32l)
    )

def cmd_write_lut_t():
    return cstruct.Struct(
        "inst" / block_loc_t(),
        "offset" / cstruct.Int8ul,
        "n" / cstruct.Int8ul
    )


def cmd_disable_t():
    return cstruct.Struct(
        "inst" / block_loc_t()
    )


def cmd_calib_t():
    return cstruct.Struct(
        "calib_obj" / cstruct.Int8ul,
        cstruct.Padding(1),
        "inst" / block_loc_t()
    )


def circ_cmd_data():
    return cstruct.Union(None,
                         write_lut=cmd_write_lut_t(),
                         connect=cmd_connection_t(),
                         set_state=cmd_set_state_t(),
                         calibrate=cmd_calib_t(),
                         disable=cmd_disable_t(),
                         profile=cmd_profile_t()
    )

def circ_cmd_t():
        return cstruct.Struct(
            "type" / circ_cmd_type(),
            cstruct.Padding(1),
            "data" / circ_cmd_data()
        )

def validate(struct,data):
    struct.build(data)
    return data

def build_block_loc(blk,loc):
  assert(len(loc) == 4)
  addr = loc.address
  return validate(block_loc_t(), {
    'block':llenums.BlockType(blk.name).name,
    'chip':addr[0],
    'tile':addr[1],
    'slice':addr[2],
    'idx':addr[3]
  })

def build_port_loc(blk,loc,port):
  assert(len(loc) == 4)
  return validate(port_loc_t(), { \
    'inst':build_block_loc(blk,loc), \
    'port':PortType(port).name})

def build_circ_cmd(cmdtype,cmddata):
    return validate(circ_cmd_t(), {
        'type': cmdtype.name,
        'data': {cmdtype.value:cmddata}
    })
