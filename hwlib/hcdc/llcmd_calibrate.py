import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.adp as adplib

from hwlib.hcdc.llcmd_util import *


def calibrate(runtime,blk,loc,adp, \
              method=llenums.CalibrateObjective.MAXIMIZE_FIT):
    dev = hcdclib.get_device()
    state_t = {blk.name:blk.state.concretize(adp,loc)}
    # build set state command
    loc_t,loc_d = make_block_loc_t(blk,loc)
    set_state_data = {"inst": loc_d,
                      "state":state_t}
    cmd_t, cmd_data = make_circ_cmd(llenums.CircCmdType.SET_STATE,
                             set_state_data)
    cmd = cmd_t.build(cmd_data,debug=True)
    # execute set state command
    print("-> setting state")
    runtime.execute(cmd)
    resp = unpack_response(runtime.result())

    cmd_t, cmd_data = make_circ_cmd(llenums.CircCmdType.GET_STATE,
                             set_state_data)
    cmd = cmd_t.build(cmd_data,debug=True)
    # execute set state command

    calibrate_data = {"calib_obj": method.name, \
                      "inst": loc_d}
    cmd_t, cmd_data = make_circ_cmd(llenums.CircCmdType.CALIBRATE,
                             calibrate_data)

    print("-> calibrating block")
    cmd = cmd_t.build(cmd_data,debug=True)
    runtime.execute(cmd)
 
    resp = unpack_response(runtime.result())
    state = resp[blk.name]
    print("response: %s" % str(state))

    new_adp= adplib.ADP()
    new_adp.add_instance(blk,loc)
    blk.state.lift(new_adp,loc,dict(state))
    blkcfg = new_adp.configs.get(blk.name,loc)
    return blkcfg
