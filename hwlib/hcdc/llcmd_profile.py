import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd_util as llutil
import hwlib.physdb as physdblib
import hwlib.adp as adplib

def profile(runtime,dev, \
            blk,loc,adp,output_port, \
            inputs, \
            method=llenums.ProfileOpType.INPUT_OUTPUT):
    state_t = {blk.name:blk.state.concretize(adp,loc)}
    # build profiling command
    loc_t,loc_d = llutil.make_block_loc_t(blk,loc)
    values = [0.0]*2
    for input_ident,input_val in inputs.items():
        values[input_ident.code()] = input_val

    profile_data = {"method": method.name, \
                    "inst": loc_d,
                    "in_vals": values, \
                    "state":state_t,
                    "output":output_port.name}

    cmd_t, cmd_data = llutil.make_circ_cmd(llenums.CircCmdType.PROFILE,
                             profile_data)
    cmd = cmd_t.build(cmd_data,debug=True)
    # execute profiling command
    runtime.execute(cmd)
    resp = llutil.unpack_response(runtime.result())

    # reconstruct analog device program
    new_adp= adplib.ADP()
    blk,loc = llutil.from_block_loc_t(dev,resp['spec']['inst'])
    new_adp.add_instance(blk,loc)
    state = resp['spec']['state'][blk.name]
    blk.state.lift(new_adp,loc,dict(state))

    # retrieve parameters for new result
    inputs = {}
    port = llutil.get_by_ll_identifier(blk.inputs,llenums.PortType.IN0)
    if not port is None:
        inputs[port.name] = resp['spec']['in_vals'][llenums.PortType.IN0.code()]

    port = llutil.get_by_ll_identifier(blk.inputs,llenums.PortType.IN1)
    if not port is None:
        inputs[port.name]= resp['spec']['in_vals'][llenums.PortType.IN1.code()]

    new_out = llutil.get_by_ll_identifier(blk.outputs,  \
                                llenums.PortType \
                                   .from_code(int(resp['spec']['output'])))

    new_method = llenums.ProfileOpType.from_code(int(resp['spec']['method']))
    out_mean = resp['mean']
    out_std = resp['stdev']
    out_status = llenums.ProfileStatus.from_code(int(resp['status']))

    # insert into database
    blkcfg = new_adp.configs.get(blk.name,loc)
    row = physdblib.ExpCfgBlock(dev.physdb, \
                             blk,loc,new_out,blkcfg, \
                             status_type=dev.profile_status_type, \
                             method_type=dev.profile_op_type)
    row.update()
    row.add_datapoint(blkcfg, \
                      inputs, \
                      status=out_status, \
                      method=new_method, \
                      mean=out_mean, \
                      std=out_std)

    return blkcfg
