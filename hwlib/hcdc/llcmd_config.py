import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.block as blocklib
import hwlib.adp as adplib
import runtime.models.exp_delta_model as exp_delta_lib
import compiler.lscale_pass.lscale_ops as lscalelib
import hwlib.hcdc.llcmd_compensate as llcmdcomp

import ops.generic_op as genoplib
from hwlib.hcdc.llcmd_util import *

def write_lut(runtime,board,blk,loc,adp):
    cfg = adp.configs.get(blk.name,loc)
    do_compensate = adp.metadata[adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD]  \
        != lscalelib.ScaleMethod.IDEAL

    llcmdcomp.compute_expression_fields(board, \
                                        adp, \
                                        cfg, \
                                        compensate=do_compensate)

    expr_data_field = 'e'
    expr_cfg = cfg[expr_data_field]
    data = blk.data[expr_data_field]
    lut_outs = expr_cfg.outputs

    assert(len(lut_outs) == 256)
    loc_t,loc_d = make_block_loc_t(blk,loc)
    chunksize = 48
    print("expr: %s" % final_expr)
    print("# values: %d" % len(lut_outs))
    for offset,values in divide_list_into_chunks(lut_outs,chunksize):
        print("-> writing values %d-%d" % (offset,offset+len(values)))
        header = {'inst':loc_d,'offset':offset,'n':len(values)}
        cmd_t,cmd_data = make_circ_cmd(llenums.CircCmdType.WRITE_LUT, \
                                       header)
        payload_t,payload_d = make_dataset_t(values)
        cmd = cmd_t.build(cmd_data,debug=True)
        runtime.execute_with_payload(cmd,payload_d)
        resp = unpack_response(runtime.result())

def set_state(runtime,board,blk,loc,adp):
    assert(isinstance(adp,adplib.ADP))
    if not llenums.BlockType(blk.ll_name).has_state():
        print("[SKIPPING] %s.%s no state required" % (blk.name,loc))
        return


    cfg = adp.configs.get(blk.name,loc)
    do_compensate = adp.metadata[adplib.ADPMetadata.Keys.LSCALE_SCALE_METHOD]  \
        != lscalelib.ScaleMethod.IDEAL

    llcmdcomp.compute_constant_fields(board,adp,cfg,compensate=do_compensate)

    block_state = blk.state.concretize(adp,loc)
    state_t = {blk.name:block_state}
    loc_t,loc_d = make_block_loc_t(blk,loc)
    state_data = {'inst':loc_d, 'state':state_t}
    cmd_t,cmd_data = make_circ_cmd(llenums.CircCmdType.SET_STATE, \
                                       state_data)
    cmd = cmd_t.build(cmd_data,debug=True)
    runtime.execute(cmd)
    return unpack_response(runtime.result())




def set_conn(runtime,src_blk,src_loc,src_port, \
             dest_blk,dest_loc,dest_port):
    if dest_blk.name == 'lut' or \
       src_blk.name == 'lut':
        return

    ident = src_blk.outputs[src_port].ll_identifier
    sloc_t,sloc_d = make_port_loc(src_blk,src_loc,ident)

    ident = dest_blk.inputs[dest_port].ll_identifier
    dloc_t,dloc_d = make_port_loc(dest_blk,dest_loc, \
                                  ident)
    conn_data = {"src":sloc_d, "dest":dloc_d}
    cmd_t,cmd_data = make_circ_cmd(llenums.CircCmdType.CONNECT, \
                                   conn_data)
    cmd = cmd_t.build(cmd_data,debug=True)
    runtime.execute(cmd)
    return unpack_response(runtime.result())



def disable(runtime,blk,loc):
    loc_t,loc_d = make_block_loc_t(blk,loc)
    cmd_t,cmd_d = make_circ_cmd(llenums.CircCmdType.DISABLE,  \
                                          {'inst':loc_d})
    cmd = cmd_t.build(cmd_d,debug=True)
    runtime.execute(cmd)
    return unpack_response(runtime.result())
