
def derive_delta_models_adp(args):
    board = get_device(args.model_number)
    with open(args.adp,'r') as fh:
        adp = ADP.from_json(board, \
                            json.loads(fh.read()))

    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            for expmodel in physapi.get_configured_physical_block(board.physdb, \
                                                                  board, \
                                                                  blk, \
                                                                  cfg.inst.loc, \
                                                                  cfg):
                if len(expmodel.dataset) >= args.min_points and \
                   not expmodel.delta_model.complete:
                    fitlib.fit_delta_model(expmodel)
