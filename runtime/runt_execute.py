import dslang.dsprog as dsproglib

import hwlib.hcdc.llcmd as llcmd
from hwlib.adp import ADP,ADPMetadata
import hwlib.block as blocklib

import runtime.runtime_util as runtime_util

import lab_bench.devices.sigilent_osc as osclib
import lab_bench.devices.sigilent_osc_lib as oscliblib

import util.config as configlib

import json

def test_osc(args):
    board = runtime_util \
            .get_device(args.model_number,layout=False)

    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))


    prog_name = adp.metadata.get(ADPMetadata.Keys.DSNAME)
    program = dsproglib.DSProgDB.get_prog(prog_name)
    if args.no_osc:
        osc = osclib.DummySigilent1020XEOscilloscope()
    else:
        osc = osclib.Sigilent1020XEOscilloscope(configlib.OSC_IP, \
                                                configlib.OSC_PORT)
        osc.setup()


    sim_time = program.max_time
    if args.runtime:
        sim_time= args.runtime

    llcmd.test_oscilloscope(board,osc,program,adp,sim_time)

def exec_adp(args):
    board =  board = runtime_util \
                     .get_device(args.model_number,layout=True)
 
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))


    prog_name = adp.metadata.get(ADPMetadata.Keys.DSNAME)
    program = dsproglib.DSProgDB.get_prog(prog_name)
    if args.no_osc:
        osc = osclib.DummySigilent1020XEOscilloscope()
    else:
        osc = osclib.Sigilent1020XEOscilloscope(configlib.OSC_IP, \
                                                configlib.OSC_PORT)
        osc.setup()

    sim_time = program.max_time
    if args.runtime:
        sim_time= args.runtime

    runtime = GrendelRunner()
    runtime.initialize()
    for conn in adp.conns:
        sblk = board.get_block(conn.source_inst.block)
        dblk = board.get_block(conn.dest_inst.block)
        llcmd.set_conn(runtime,sblk,conn.source_inst.loc, \
                       conn.source_port, \
                       dblk,conn.dest_inst.loc, \
                       conn.dest_port)

    calib_obj = adp.metadata[adplib.ADPMetadata.Keys.CALIB_OBJ]
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        resp = llcmd.set_state(runtime, \
                               board,
                               blk, \
                               cfg.inst.loc, \
                               adp, \
                               calib_obj=calib_obj)

    llcmd.execute_simulation(runtime,board, \
                             program, adp,\
                             sim_time=sim_time, \
                             osc=osc, \
                             manual=False)
    runtime.close()
