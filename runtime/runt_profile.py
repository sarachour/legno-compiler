
def profile_adp(args):
    board = get_device(args.model_number)
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))

    runtime = GrendelRunner()
    runtime.initialize()
    label = physutil.DeltaModelLabel(args.method)
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            for expmodel in physapi.get_calibrated_configured_physical_block(board.physdb, \
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

