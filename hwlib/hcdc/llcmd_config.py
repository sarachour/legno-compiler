import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.block as blocklib
import hwlib.adp as adplib
import runtime.models.exp_delta_model as exp_delta_lib

from hwlib.hcdc.llcmd_util import *

def set_state(runtime,board,blk,loc,adp, \
              calib_obj=llenums.CalibrateObjective.MINIMIZE_ERROR):
    assert(isinstance(adp,adplib.ADP))
    if not llenums.BlockType(blk.ll_name).has_state():
        print("[SKIPPING] %s.%s no state required" % (blk.name,loc))
        return


    cfg = adp.configs.get(blk.name,loc)
    calib_cfgs = exp_delta_lib.get_calibrated(board,blk,loc,cfg,calib_obj)
    if len(calib_cfgs) == 0:
        print(cfg)
        raise Exception("not calibrated model_number=%s calib=%s" % (board.model_number, \
                                                                     calib_obj))

    calib_cfg = calib_cfgs[0]

    for st in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), \
                     blk.state):
        cfg[st.name].value = calib_cfg.config[st.name].value

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
    ident = src_blk.outputs[src_port].ll_identifier
    sloc_t,sloc_d = make_port_loc(src_blk,src_loc,ident)

    ident = src_blk.inputs[dest_port].ll_identifier
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
