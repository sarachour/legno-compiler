from hwlib.adp import ADP,ADPMetadata
from lab_bench.grendel_runner import GrendelRunner
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import dslang.dsprog as dsproglib
import lab_bench.devices.sigilent_osc as osclib
import json

def get_device():
    import hwlib.hcdc.hcdcv2 as hcdclib
    return hcdclib.get_device(layout=False)


def characterize_adp():
    raise NotImplementedError

def calibrate_adp(args):
    board = get_device()
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))

    runtime = GrendelRunner()
    runtime.initialize()
    method = llenums.CalibrateObjective(args.method)
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            upd_cfg = llcmd.calibrate(runtime, \
                                      blk, \
                                      cfg.inst.loc,\
                                      adp, \
                                      method=method)
            #exp = ExpCfgBlock(db,blk,loc,output_port,upd_cfg, \
            #                  status_type=None, \
            #                  method_type=None)
            #print(upd_cfg)

            raise NotImplementedError

def exec_adp(args):
    board = get_device()
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))


    prog_name = adp.metadata.get(ADPMetadata.Keys.DSNAME)
    program = dsproglib.DSProgDB.get_prog(prog_name)
    osc = osclib.DummySigilent1020XEOscilloscope()

    sim_time= None
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

    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        resp = llcmd.set_state(runtime, \
                               board,
                               blk, \
                               cfg.inst.loc, \
                               adp)

    llcmd.execute_simulation(runtime,board, \
                             program, adp,\
                             sim_time=sim_time, \
                             osc=osc, \
                             manual=False)
    runtime.close()
