
def get_num_characterized_codes(board,blk,cfg):
    return len(list(physapi.get_by_block_configuration(board.physdb, \
                                                       board, \
                                                       blk, \
                                                       cfg)))


def characterize_adp(args):
    board = get_device(args.model_number,layout=True)
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
            curr_hidden_codes = get_num_characterized_codes(board,blk,cfg)
            if curr_hidden_codes >= args.num_hidden_codes*args.num_locs:
                continue

            curr_num_locs = math.floor(curr_hidden_codes/args.num_hidden_codes)
            num_new_locs = args.num_locs - curr_num_locs
            assert(curr_num_locs > 0)

            upd_cfg = llcmd.characterize(runtime, \
                                         board, \
                                         blk, \
                                         cfg, \
                                         grid_size=args.grid_size, \
                                         num_locs=args.num_locs, \
                                         num_hidden_codes=args.num_hidden_codes)

