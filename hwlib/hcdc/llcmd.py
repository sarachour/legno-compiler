import hwlib.device as devlib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.hcdc.llenums as llenums
import hwlib.physdb as physdb

import lab_bench.grendel_util as grendel_util

def get_by_ll_identifier(collection,ident):
    for port in collection:
        if port.ll_identifier == ident:
            return port


def from_block_loc_t(dict_):
    dev = hcdclib.get_device()
    chip = dict_['chip']
    tile = dict_['tile']
    slice_ = dict_['slice']
    idx = dict_['idx']
    block_type = llenums.BlockType.by_name(str(dict_['block']))
    blk = dev.get_block(block_type.value)
    addr = [int(dict_['chip']), \
            int(dict_['tile']), \
            int(dict_['slice']), \
            int(dict_['idx'])]
    return blk,devlib.Location(addr)

def make_block_loc_t(blk,loc):
  assert(len(loc) == 4)
  if isinstance(blk,str):
      block_name = blk
  else:
      block_name = blk.name


  addr = loc.address
  loc = {
    'block':llenums.BlockType(block_name).name,
    'chip':addr[0],
    'tile':addr[1],
    'slice':addr[2],
    'idx':addr[3]
  }
  return llstructs.block_loc_t(),loc

def make_port_loc(blk,loc,port):
  assert(len(loc) == 4)
  if isinstance(blk,str):
      block_name = blk
  else:
      block_name = blk.name

  addr = loc.address
  loc = {
    'block':llenums.BlockType(block_name).name,
    'chip':addr[0],
    'tile':addr[1],
    'slice':addr[2],
    'idx':addr[3]
  }
  loc = { \
          'loc':loc, \
          'port':llenums.PortType(port).name}

  return llstructs.port_loc_t(),loc

def make_exp_cmd(cmdtype,args,flag):
    assert(isinstance(cmdtype,llenums.ExpCmdType))
    assert('ints' in args or 'floats' in args)
    cmd_d = {
        "cmd_type": llenums.CmdType.EXPERIMENT_CMD.name,
        "cmd_data":{
            "exper_cmd": {
                'type': cmdtype.name,
                'args': args,
                'flag': flag
            }
        }
    }
    return llstructs.cmd_t(),cmd_d


def make_circ_cmd(cmdtype,cmddata):
    assert(isinstance(cmdtype,llenums.CircCmdType))
    cmd_d = {
        "cmd_type": llenums.CmdType.CIRC_CMD.name,
        "cmd_data":{
            "circ_cmd": {
                'circ_cmd_type': cmdtype.name,
                'circ_cmd_data': {cmdtype.value:cmddata}
            }
        }
    }
    return llstructs.cmd_t(),cmd_d

def _unpack_response(resp):
  if isinstance(resp,grendel_util.HeaderArduinoResponse):
    if resp.num_args == 1:
      return _unpack_response(resp.data(0))
    elif resp.num_args == 0:
      return resp.message
    else:
      raise Exception("only can handle responses with one or zero data segments")

  elif isinstance(resp,grendel_util.DataArduinoResponse):
    assert(isinstance(resp.value,grendel_util.PayloadArduinoResponse))
    return _unpack_response(resp.value)

  elif isinstance(resp,grendel_util.PayloadArduinoResponse):
    payload_type = llstructs.parse(llstructs.response_type_t(), \
                                   bytes([resp.payload_type]))
    payload_result = None
    if payload_type == llenums.ResponseType.BLOCK_STATE.value:
      payload_result = llstructs.parse(llstructs.state_t(), \
                                       resp.array)
    elif payload_type == llenums.ResponseType.PROFILE_RESULT.value:
      payload_result = llstructs.parse(llstructs.profile_result_t(), \
                                       resp.array)

    return payload_result

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
    resp = _unpack_response(runtime.result())

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
    
    resp = _unpack_response(runtime.result())
    state = resp[blk.name]
    new_adp= adplib.ADP()
    new_adp.add_instance(blk,loc)
    blk.state.lift(new_adp,loc,dict(state))
    blkcfg = new_adp.configs.get(blk.name,loc)
    return blkcfg

def profile(runtime,blk,loc,adp,output_port, \
            inputs, \
            method=llenums.ProfileOpType.INPUT_OUTPUT):
    dev = hcdclib.get_device()
    state_t = {blk.name:blk.state.concretize(adp,loc)}
    # build profiling command
    loc_t,loc_d = make_block_loc_t(blk,loc)
    values = [0.0]*2
    for input_ident,input_val in inputs.items():
        values[input_ident.code()] = input_val

    profile_data = {"method": method.name, \
                    "inst": loc_d,
                    "in_vals": values, \
                    "state":state_t,
                    "output":output_port.name}

    cmd_t, cmd_data = make_circ_cmd(llenums.CircCmdType.PROFILE,
                             profile_data)
    cmd = cmd_t.build(cmd_data,debug=True)
    # execute profiling command
    runtime.execute(cmd)
    resp = _unpack_response(runtime.result())

    # reconstruct analog device program
    new_adp= adplib.ADP()
    blk,loc = from_block_loc_t(resp['spec']['inst'])
    new_adp.add_instance(blk,loc)
    state = resp['spec']['state'][blk.name]
    blk.state.lift(new_adp,loc,dict(state))

    # retrieve parameters for new result
    inputs = {}
    port = get_by_ll_identifier(blk.inputs,llenums.PortType.IN0)
    if not port is None:
        inputs[port.name] = resp['spec']['in_vals'][llenums.PortType.IN0.code()]

    port = get_by_ll_identifier(blk.inputs,llenums.PortType.IN1)
    if not port is None:
        inputs[port.name]= resp['spec']['in_vals'][llenums.PortType.IN1.code()]

    new_out = get_by_ll_identifier(blk.outputs,  \
                                llenums.PortType \
                                   .from_code(int(resp['spec']['output'])))

    new_method = llenums.ProfileOpType.from_code(int(resp['spec']['method']))
    out_mean = resp['mean']
    out_std = resp['stdev']
    out_status = llenums.ProfileStatus.from_code(int(resp['status']))

    # insert into database
    blkcfg = new_adp.configs.get(blk.name,loc)
    db = physdb.PhysicalDatabase(runtime.board_name)
    row = physdb.ExpCfgBlock(db,blk,loc,new_out,blkcfg, \
                              dev.profile_status_type, \
                              dev.profile_op_type)
    row.update()
    row.add_datapoint(blkcfg, \
                      inputs, \
                      status=out_status, \
                      method=new_method, \
                      mean=out_mean, \
                      std=out_std)

    return blkcfg

def set_state(runtime,blk,loc,adp):
    assert(isinstance(adp,adplib.ADP))
    block_state = blk.state.concretize(adp,loc)
    print("state: %s" % block_state)
    state_t = {blk.name:block_state}
    loc_t,loc_d = make_block_loc_t(blk,loc)
    state_data = {'inst':loc_d, 'state':state_t}
    cmd_t,cmd_data = make_circ_cmd(llenums.CircCmdType.SET_STATE, \
                                       state_data)
    cmd = cmd_t.build(cmd_data,debug=True)
    runtime.execute(cmd)
    return _unpack_response(runtime.result())

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
    return _unpack_response(runtime.result())

def get_external_outputs(board,adp):
  for cfg in adp.configs:
    block_inst = cfg.inst
    blk = board.get_block(cfg.inst.block)
    print(cfg.inst)
  raise Exception("unimpl")


def to_volt_ranges(board,dsprog,adp):
  '''  
  def scale(scf,lb,ub,slack=1.1):
    rng = (ub-lb)*scf/2
    midpoint = (ub+lb)/2.0
    slb = max((midpoint-rng*slack),lb)
    sub = min((midpoint+rng*slack),ub)
    return slb,sub


  extern_outs = get_external_outputs(board,adp)

  for handle, info in adcs_in_use.items():
    out_no = hwenv.adc(handle)
    pin_mode = hwenv.oscilloscope.output(handle)
    if isinstance(pin_mode,DiffPinMode):
      llb,lub  = hwenv.oscilloscope.chan_range(pin_mode.low)
      hlb,hub  = hwenv.oscilloscope.chan_range(pin_mode.high)
      sig_range = info['scf']*info['interval'].bound
      hw_range = max(abs(hub-llb),abs(hlb-lub))
      scf = sig_range/hw_range
      slb,sub = scale(scf,llb,lub)
      yield pin_mode.low,slb,sub
      slb,sub = scale(scf,hlb,hub)
      yield pin_mode.high,slb,sub

    else:
      raise Exception("None")
  '''  
  raise Exception("Adapt voltage range statements")

def get_sim_time(board,dsprog,adp):
    if sim_time is None:
        sim_time = dsprog.max_time

    if dsprog.max_time < sim_time:
        raise Exception("cannot execute simulation: maximum runtime is %s" % dsprog.max_time)

    hwtime = board.time_constant
    time_us = sim_time*adp.tau*hwtime
    return time_us


def configure_oscilloscope(osc,board,dsprog,adp):
    '''
    for chan,lb,ub in to_volt_ranges(board, \
                                     dsprog, \
                                     adp):
       cmd = "osc_set_volt_range %d %f %f" \
             % (chan,lb,ub)
       gren.add(parse(cmd))
       cmd = "osc_set_sim_time %.3e" % \
             (scaled_sim_time*osc_slack)
       gren.add(parse(cmd))

    gren.add(parse('osc_setup_trigger'))
    '''
    raise Exception("TODO: adapt oscilloscope configuration statements")

def execute_simulation(runtime,board,dsprog,adp,sim_time=None,osc=None,manual=False):
    def dispatch(cmd_type,data,flag):
        cmd_t,cmd_data = make_exp_cmd(cmd_type,data,flag)
        cmd = cmd_t.build(cmd_data,debug=True)
        runtime.execute(cmd)
        return _unpack_response(runtime.result())

    osc = "DUMMY"
    noargs = {'ints':[0,0,0]}
    print("=== enabling flags ===")
    dispatch(llenums.ExpCmdType.USE_ANALOG_CHIP,noargs,0)
    if not osc is None:
        print("=== configuring scope ===")
        dispatch(llenums.ExpCmdType.USE_OSC,noargs,0)
        configure_oscilloscope(osc,board,dsprog,adp)

    if sim_time is None:
        sim_time = dsprog.max_time

    if dsprog.max_time < sim_time:
        raise Exception("cannot execute simulation: maximum runtime is %s" % dsprog.max_time)

    print("=== writing simulation time ===")
    time_us = get_sim_time(board,dsprog,adp)
    simargs = {'floats':[time_us,0.0,0.0]}
    dispatch(llenums.ExpCmdType.SET_SIM_TIME,simargs,0)


    if manual:
        input("waiting for input:")

    dispatch(llenums.ExpCmdType.RUN,noargs,0)

    if not osc is None:
        print("=== retrieving data ===")

def disable(runtime,blk,loc):
    loc_t,loc_d = make_block_loc_t(blk,loc)
    cmd_t,cmd_d = make_circ_cmd(llenums.CircCmdType.DISABLE,  \
                                          {'inst':loc_d})
    cmd = cmd_t.build(cmd_d,debug=True)
    runtime.execute(cmd)
    return _unpack_response(runtime.result())
