
def calibrate_adp(args):
    board = get_device(args.model_number)
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))

    runtime = GrendelRunner()
    runtime.initialize()
    method = llenums.CalibrateObjective(args.method)
    delta_model_label = physutil.DeltaModelLabel \
                                 .from_calibration_objective(method, \
                                                             legacy=True)
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)


        cfg_modes = cfg.modes
        for mode in widenlib.widen_modes(blk,cfg):
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
                exp = deltalib.ExpCfgBlock(board.physdb, \
                                           board, \
                                           blk, \
                                           cfg.inst.loc,output, \
                                           upd_cfg, \
                                           status_type=board.profile_status_type, \
                                           method_type=board.profile_op_type)
                exp.delta_model.label = delta_model_label
                exp.update()
