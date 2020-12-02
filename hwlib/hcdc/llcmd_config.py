import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.block as blocklib
import hwlib.adp as adplib
import runtime.models.exp_delta_model as exp_delta_lib

import ops.generic_op as genoplib
from hwlib.hcdc.llcmd_util import *

def write_lut(runtime,board,blk,loc,adp, \
              calib_obj=llenums.CalibrateObjective.MINIMIZE_ERROR):
    cfg = adp.configs.get(blk.name,loc)
    input_port = blk.inputs.singleton()
    output_port = blk.outputs.singleton()

    expr_data_field = 'e'
    expr_cfg = cfg[expr_data_field]
    data = blk.data[expr_data_field]
    assert(isinstance(expr_cfg,adplib.ExprDataConfig))
    repls = {}
    for inp in data.inputs:
        inj = expr_cfg.injs[inp]
        repls[inp] = genoplib.Mult( \
                                    genoplib.Const(inj), \
                                    genoplib.Var(inp))

    inj = expr_cfg.injs[expr_data_field]
    func_impl = genoplib.Mult(genoplib.Const(inj), \
                              expr_cfg.expr.substitute(repls))

    rel = output_port.relation[cfg.mode] \
                     .substitute({expr_data_field:func_impl})
    final_expr = rel.concretize()

    print(final_expr)
    lut_outs = []
    for val in input_port.quantize[cfg.mode] \
                             .get_values(input_port \
                                         .interval[cfg.mode]):
        out = final_expr.compute({input_port.name:val})
        lut_outs.append(out)

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


def _add_calibration_codes(board,blk,loc,cfg,calib_obj):
    calib_codes = list(filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), \
                              blk.state))

    if len(calib_codes) == 0:
        return

    calib_cfgs = exp_delta_lib.get_calibrated(board,blk,loc,cfg,calib_obj)
    if len(calib_cfgs) == 0:
        print(cfg)
        raise Exception("not calibrated model_number=%s calib=%s" % (board.model_number, \
                                                                    calib_obj))

    calib_cfg = calib_cfgs[0]

    for st in calib_codes:
        cfg[st.name].value = calib_cfg.config[st.name].value

    return calib_cfg

def _compensate_for_offsets(blk,cfg,calib_cfg):
    if calib_cfg is None:
        return

    ll_corr_pars = calib_cfg.spec \
                            .get_params_of_type(blocklib.DeltaParamType.LL_CORRECTABLE)
    if len(blk.data) < 1:
        return

    if len(ll_corr_pars) == 1:
        assert(len(blk.data) == 1)
        data_field = blk.data.singleton().name
        corr_par = ll_corr_pars[0]
        old_val = cfg[data_field].value
        cfg[data_field].value -= calib_cfg.get_value(corr_par.name)/cfg[data_field].scf
        print("=> updated data field %s : %f -> %f" % (data_field, old_val, \
                                                       cfg[data_field].value))

def set_state(runtime,board,blk,loc,adp, \
              calib_obj=llenums.CalibrateObjective.MINIMIZE_ERROR):
    assert(isinstance(adp,adplib.ADP))
    if not llenums.BlockType(blk.ll_name).has_state():
        print("[SKIPPING] %s.%s no state required" % (blk.name,loc))
        return


    cfg = adp.configs.get(blk.name,loc)
    calib_cfg = _add_calibration_codes(board,blk,loc,cfg,calib_obj)
    _compensate_for_offsets(blk,cfg,calib_cfg)

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
