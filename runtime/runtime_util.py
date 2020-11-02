from hwlib.adp import ADP,ADPMetadata
from lab_bench.grendel_runner import GrendelRunner
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd

import json

def get_device():
    import hwlib.hcdc.hcdcv2 as hcdclib
    return hcdclib.get_device(layout=False)


def exec_adp(args):
    board = get_device()
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))


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
                               blk, \
                               cfg.inst.loc, \
                               cfg)
        print(resp)

    runtime.close()
