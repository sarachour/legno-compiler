from hwlib.adp import ADP,ADPMetadata
from lab_bench.grendel_runner import GrendelRunner
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import dslang.dsprog as dsproglib
import lab_bench.devices.sigilent_osc as osclib
import phys_model.model_fit as fitlib
import phys_model.planner as planlib
import phys_model.profiler as proflib
import hwlib.physdb as physdblib
import json

def get_device(model_no,layout=False):
    assert(not model_no is None)
    import hwlib.hcdc.hcdcv2 as hcdclib
    return hcdclib.get_device(model_no,layout=layout)

def update_dectree_data(blk,loc,exp_mdl, \
                        params, model_errors, \
                        hidden_codes):

    key = (blk.name,loc)
    if not key in params:
        params[key] = {}
        model_errors[key] = []
        hidden_codes[key] = {}

    for par,value in exp_mdl.delta_model.params.items():
        if not par in params[key]:
            params[key][par] = []

        params[key][par].append(value)

    for hidden_code,value in exp_mdl.hidden_codes():
        if not hidden_code in hidden_codes[key]:
            hidden_codes[key][hidden_code] = []
        hidden_codes[key][hidden_code].append(value)

    model_errors[key].append(exp_mdl.delta_model.model_error)


def mktree_adp(args):
    dev = get_device(args.model_number,layout=True)
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(dev, \
                            json.loads(fh.read()))

    for cfg in adp.configs:
        blk = dev.get_block(cfg.inst.block)
        for mode in blk.modes:
            cfg.modes = [mode]

            params = {}
            hidden_codes = {}
            model_errors = {}
            for exp_mdl in physdblib.get_by_block_configuration(dev.physdb, \
                                                            dev, blk, cfg):
                if len(exp_mdl.dataset) == 0:
                    continue

                fitlib.fit_delta_model(exp_mdl,operation=llenums.ProfileOpType.INTEG_INITIAL_COND)
                if not exp_mdl.delta_model.complete:
                    print("[WARN] incomplete delta model!")
                    continue

                update_dectree_data(blk,exp_mdl.loc,exp_mdl, \
                                    params,model_errors, \
                                    hidden_codes)

            print("collected data")
            for blk,loc in model_errors.keys():
                print("--- fitting decision tree (%d samples) ---" % n_samples)
                output = costs
                dectree,predictions = fit_lindectree.fit_decision_tree(hidden_codes, \
                                                                       inputs,output, \
                                                                       max_depth, \
                                                                       min_size)


            input()

def characterize_adp(args):
    board = get_device(args.model_number,layout=True)
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))

    runtime = GrendelRunner()
    runtime.initialize()
    print("TODO: don't characterize the same configured block multiple times")
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            upd_cfg = llcmd.characterize(runtime, \
                                         board, \
                                         blk, \
                                         cfg, \
                                         grid_size=args.grid_size, \
                                         num_locs=args.num_locs, \
                                         num_hidden_codes=args.num_hidden_codes)
            #exp = ExpCfgBlock(db,blk,loc,output_port,upd_cfg, \
            #                  status_type=None, \
            #                  method_type=None)
            #print(upd_cfg)

            raise NotImplementedError


    raise NotImplementedError


def profile_adp(args):
    board = get_device(args.model_number)
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))

    runtime = GrendelRunner()
    runtime.initialize()
    label = physdblib.DeltaModelLabel(args.method)
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            for expmodel in physdblib.get_calibrated_configured_physical_block(board.physdb, \
                                                                               board, \
                                                                               blk, \
                                                                               cfg.inst.loc, \
                                                                               cfg, \
                                                                               label):
                if len(expmodel.dataset) >= args.max_points:
                    continue

                print("==== profile %s[%s] %s (npts=%d)"\
                      % (blk.name,cfg.inst.loc,mode,len(expmodel.dataset)))
                print(expmodel.cfg)
                planner = planlib.SingleDefaultPointPlanner(blk, cfg.inst.loc, expmodel.cfg,
                                                            n=args.grid_size,
                                                            m=args.grid_size)
                proflib.profile_all_hidden_states(runtime, board, planner)


def derive_delta_models_adp(args):
    board = get_device(args.model_number)
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))

    runtime = GrendelRunner()
    runtime.initialize()
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            for expmodel in physdblib.get_configured_physical_block(board.physdb, \
                                                                    board, \
                                                                    blk, \
                                                                    cfg.inst.loc, \
                                                                    cfg):
                if len(expmodel.dataset) >= args.min_points and \
                   not expmodel.delta_model.complete:
                    fitlib.fit_delta_model(expmodel)

def is_calibrated(board,blk,loc,cfg,label):
    for it in physdblib.get_calibrated_configured_physical_block(board.physdb, \
                                                                 board, \
                                                                 blk, \
                                                                 loc, \
                                                                 cfg, \
                                                                 label):
        return True

    return False

def calibrate_adp(args):
    board = get_device(args.model_number)
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))

    runtime = GrendelRunner()
    runtime.initialize()
    method = llenums.CalibrateObjective(args.method)
    delta_model_label = physdblib.DeltaModelLabel \
                                 .from_calibration_objective(method, \
                                                             legacy=True)
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)


        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            if not blk.requires_calibration():
                continue

            print("%s" % (cfg.inst))
            print(cfg)
            print('----')

            if is_calibrated(board,blk,cfg.inst.loc, \
                             cfg,delta_model_label):
                print("-> already calibrated")
                continue

            upd_cfg = llcmd.calibrate(runtime, \
                                      board, \
                                      blk, \
                                      cfg.inst.loc,\
                                      adp, \
                                      method=method)
            for output in blk.outputs:
                exp = physdblib.ExpCfgBlock(board.physdb, \
                                            blk, \
                                            cfg.inst.loc,output, \
                                            upd_cfg, \
                                            status_type=board.profile_status_type, \
                                            method_type=board.profile_op_type)
                exp.delta_model.label = delta_model_label
                exp.update()

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
