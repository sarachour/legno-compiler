import hwlib.block as blocklib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.adp as adplib
import util.paths as pathlib
import util.util as util


import lab_bench.devices.sigilent_osc_lib as oscliblib
import lab_bench.devices.sigilent_osc as osclib


from hwlib.hcdc.llcmd_util import *

def get_osc_chan_for_pin(pin):
    if pin == llenums.ExternalPins.OUT0:
        return osclib.Sigilent1020XEOscilloscope.Channels.ACHAN1
    elif pin == llenums.ExternalPins.OUT1:
        return osclib.Sigilent1020XEOscilloscope.Channels.ACHAN2
    else:
        raise Exception("unknown pin <%s>" % pin)


def get_wall_clock_time(board,dsprog,adp,sim_time):
    hwtime = board.time_constant
    time_us = sim_time*adp.tau*hwtime
    return time_us

def save_data_from_oscilloscope(osc,board,dsprog,adp,time,trial=0):

    ph = pathlib.PathHandler(adp.metadata[adplib.ADPMetadata.Keys.FEATURE_SUBSET], \
                             dsprog.name)

    for var,scf,chans in adp.observable_ports(board):
        chan_pos = get_osc_chan_for_pin(chans[llenums.Channels.POS].pin)
        chan_neg = get_osc_chan_for_pin(chans[llenums.Channels.NEG].pin)
        times,voltages = oscliblib.get_waveform(osc, \
                                                chan_pos, \
                                                chan_neg, \
                                                differential=True)
        tc = board.time_constant*adp.tau
        json_data = {'times':times,  \
                     'values':voltages,  \
                     'time_units': 'wall_clock_sec', \
                     'ampl_units': 'voltage', \
                     'variable':var, \
                     'time_scale':tc, \
                     'mag_scale':scf}
        print("<writing file>")

        filename = ph.measured_waveform_file(graph_index=adp.metadata[adplib.ADPMetadata.Keys.LGRAPH_ID], \
                                             scale_index=adp.metadata[adplib.ADPMetadata.Keys.LSCALE_ID], \
                                             model=adp.metadata[adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD], \
                                             opt=adp.metadata[adplib.ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                                             phys_db=adp.metadata[adplib.ADPMetadata.Keys.RUNTIME_PHYS_DB], \
                                             calib_obj=adp.metadata[adplib.ADPMetadata.Keys.RUNTIME_CALIB_OBJ], \
                                             variable=var, \
                                             trial=trial)

        with open(filename.format(variable=var),'w') as fh:
            print("-> compressing data")
            strdata = util.compress_json(json_data)
            fh.write(strdata)
        print("<wrote file>")


def configure_oscilloscope(osc,board,dsprog,adp,time):
    osc_slack = 1.1
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        for out in blk.outputs:
            for pininfo in board.get_external_pins(blk,cfg.inst.loc,out.name):
                chan = get_osc_chan_for_pin(pininfo.pin)
                port_cfg = cfg[out.name]
                unscaled_ival = dsprog.get_interval(port_cfg.source.name)
                scaled_ival = unscaled_ival.scale(port_cfg.scf*osc_slack)
                oscliblib.set_voltage_range(osc,chan,scaled_ival)

    oscliblib.set_time(osc,get_wall_clock_time(board,dsprog,adp,time)*osc_slack)
    oscliblib.set_trigger(osc)


def test_oscilloscope(board,osc,dsprog,adp,sim_time=None):
    configure_oscilloscope(osc,board,dsprog,adp,sim_time)
    save_data_from_oscilloscope(osc,board,dsprog,adp,sim_time)

def execute_simulation(runtime,board,dsprog,adp,sim_time=None,osc=None,manual=False):
    def dispatch(cmd_type,data,flag):
        cmd_t,cmd_data = make_exp_cmd(cmd_type,data,flag)
        cmd = cmd_t.build(cmd_data,debug=True)
        runtime.execute(cmd)
        return unpack_response(runtime.result())

    if sim_time is None:
        sim_time = dsprog.max_time

    if dsprog.max_time < sim_time:
        raise Exception("cannot execute simulation: maximum runtime is %s" % dsprog.max_time)

    noargs = {'ints':[0,0,0]}
    print("=== enabling flags ===")
    dispatch(llenums.ExpCmdType.USE_ANALOG_CHIP,noargs,0)

    if not osc is None:
        print("=== configuring scope ===")
        dispatch(llenums.ExpCmdType.USE_OSC,noargs,0)
        configure_oscilloscope(osc,board,dsprog,adp,sim_time)

    print("=== writing simulation time ===")
    time_sec = get_wall_clock_time(board,dsprog,adp,sim_time)
    simargs = {'floats':[time_sec,0.0,0.0]}
    dispatch(llenums.ExpCmdType.SET_SIM_TIME,simargs,0)


    if manual:
        input("waiting for input:")

    dispatch(llenums.ExpCmdType.RUN,noargs,0)

    if not osc is None:
        print("=== retrieving data ===")
        save_data_from_oscilloscope(osc,board,dsprog,adp,sim_time)
