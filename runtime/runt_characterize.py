from hwlib.adp import ADP,ADPMetadata, BlockConfig,BlockInst

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib

from lab_bench.grendel_runner import GrendelRunner

import hwlib.device as devlib

import hwlib.hcdc.llcmd_util as llutil
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import math

def count_hidden_codes(delta_models):

    return len(list(physapi.get_by_block_configuration(board.physdb, \
                                                       board, \
                                                       blk, \
                                                       cfg)))

def continue_characterization(runtime,board,datasets,block,config, \
                              grid_size,num_locs,num_hidden_codes, \
                              only_adp_locs=False):
    locs = set(map(lambda ds: ds.loc, datasets))
    datasets_by_loc = dict(map(lambda loc: (loc,set()), locs))
    for dataset in datasets:
        datasets_by_loc[dataset.loc].add(dataset.hidden_cfg)

    print("=== Continuing Characterization! ===")
    for loc,hidden_cfgs in datasets_by_loc.items():
        print("----- %s (%d/%d) ----" % (loc,len(hidden_cfgs),num_hidden_codes))
        if len(hidden_cfgs) < num_hidden_codes:
            new_hidden_codes = num_hidden_codes - len(hidden_cfgs) + 1
            print("=>> LOC=%s new-hidden-codes=%d" % (loc,new_hidden_codes))
            config.inst.loc = loc
            upd_cfg = llcmd.characterize(runtime, \
                                         board, \
                                         block, \
                                         config, \
                                         locs=[loc],
                                         grid_size=grid_size, \
                                         num_hidden_codes=new_hidden_codes)



    if len(locs) < num_locs:
        new_locs = num_locs - len(locs)
        new_characterization(runtime,board,block,config, \
                             grid_size,new_locs,num_hidden_codes, \
                             only_adp_locs)

def new_characterization(runtime,board,block,config, \
                         grid_size,num_locs,num_hidden_codes, \
                         only_adp_locs=False):
  if only_adp_locs:
     locs = [config.inst.loc]
  else:
     locs = list(llutil.random_locs(board,block,num_locs))
  print("=== New Characterization! ===")
  upd_cfg = llcmd.characterize(runtime, \
                               board, \
                               block, \
                               config, \
                               locs=locs,
                               grid_size=grid_size, \
                               num_hidden_codes=num_hidden_codes)


def characterize_configured_block(runtime,board,block,cfg, \
                                 grid_size=11, \
                                 num_locs=5, \
                                 num_hidden_codes=50, \
                                 adp_locs=False):
        datasets = list(exp_profile_dataset_lib.get_datasets(board, \
                                                             ['block','static_config'],
                                                             block=block, \
                                                             config=cfg))

        unique_hidden_codes = set(map(lambda model: str(model.loc)+"." \
                                    +model.hidden_cfg, datasets))
        total_codes = num_hidden_codes*num_locs
        if len(unique_hidden_codes) >= total_codes:
            print("block %s.%s [%s] has enough hidden codes %d/%d" % (block.name,cfg.inst.loc, cfg.mode, \
                                                                len(unique_hidden_codes),total_codes))
            return

        if len(datasets) > 0:
            continue_characterization(runtime, \
                                    board=board,
                                    block=block,
                                    config=cfg, \
                                    datasets=datasets,\
                                    grid_size=grid_size, \
                                    num_locs=num_locs, \
                                    num_hidden_codes=num_hidden_codes, \
                                    only_adp_locs=adp_locs
            )
        else:
            new_characterization(runtime, \
                                board=board,
                                block=block,
                                config=cfg, \
                                grid_size=grid_size, \
                                num_locs=num_locs, \
                                num_hidden_codes=num_hidden_codes, \
                                only_adp_locs=adp_locs
            )


def characterize_adp(args):
    board = runtime_util.get_device(args.model_number,layout=True)
    runtime = GrendelRunner()
    runtime.initialize()
    if not args.adp is None:
        adp = runtime_util.get_adp(board,args.adp,widen=args.widen)
        if args.adp_locs:
           args.num_locs = 1

        for cfg in adp.configs:
            blk = board.get_block(cfg.inst.block)
            cfg_modes = cfg.modes
            for mode in cfg_modes:
                cfg.modes = [mode]
                characterize_configured_block(runtime,board,blk,cfg, \
                                              grid_size=args.grid_size, \
                                              num_locs=args.num_locs,\
                                              num_hidden_codes=args.num_hidden_codes, \
                                              adp_locs=args.adp_locs)

    else:
        if args.adp_locs or args.widen:
            raise Exception("full board characterization doesn't accept adp-locs or widen parameters")

        for block in board.blocks:
            if not block.requires_calibration():
                continue

            for mode in block.modes:
                loc = devlib.Location(list(board.layout.instances(block.name))[0])
                cfg = BlockConfig.make(block,loc)
                cfg.modes = [mode]
                characterize_configured_block(runtime,board,block,cfg, \
                                                grid_size=args.grid_size, \
                                                num_locs=args.num_locs,\
                                                num_hidden_codes=args.num_hidden_codes, \
                                                adp_locs=False)


