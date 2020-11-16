from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as exp_delta_model_lib

from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import math

def count_hidden_codes(delta_models):

    return len(list(physapi.get_by_block_configuration(board.physdb, \
                                                       board, \
                                                       blk, \
                                                       cfg)))


def characterize_adp(args):
    board = runtime_util.get_device(args.model_number,layout=True)
    adp = runtime_util.get_adp(board,args.adp)
    runtime = GrendelRunner()
    runtime.initialize()
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            delta_models = list(exp_delta_model_lib.get_models_by_block_config(board, \
                                                                               blk, \
                                                                               cfg))
            unique_hidden_codes = set(map(lambda model: str(model.loc)+"." \
                                          +model.hidden_cfg, delta_models))
            total_codes = args.num_hidden_codes*args.num_locs
            if len(unique_hidden_codes) >= total_codes:
                continue

            curr_num_locs = math.floor(len(unique_hidden_codes)/args.num_hidden_codes)
            num_new_locs = args.num_locs - curr_num_locs
            assert(curr_num_locs >= 0)

            upd_cfg = llcmd.characterize(runtime, \
                                         board, \
                                         blk, \
                                         cfg, \
                                         grid_size=args.grid_size, \
                                         num_locs=args.num_locs, \
                                         num_hidden_codes=args.num_hidden_codes)

