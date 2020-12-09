from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib

from lab_bench.grendel_runner import GrendelRunner
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
                              grid_size,num_locs,num_hidden_codes):
    locs = set(map(lambda ds: ds.loc, datasets))
    datasets_by_loc = dict(map(lambda loc: (loc,set()), locs))
    for dataset in datasets:
        datasets_by_loc[dataset.loc].add(dataset.hidden_cfg)

    print("=== Continuing Characterization! ===")
    for loc,hidden_cfgs in datasets_by_loc.items():
        if len(hidden_cfgs) < num_hidden_codes:
            new_hidden_codes = num_hidden_codes - len(hidden_cfgs) + 1
            print("=>> LOC=%s new-hidden-codes=%d" % (loc,new_hidden_codes))
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
                             grid_size,new_locs,num_hidden_codes)

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




def characterize_adp(args):
    board = runtime_util.get_device(args.model_number,layout=True)
    adp = runtime_util.get_adp(board,args.adp,widen=args.widen)
    runtime = GrendelRunner()
    runtime.initialize()
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)
        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]

            if blk.name == "dac" and "dyn" in str(cfg.mode):
                raise Exception("TODO: cannot characterize dac in dynamic mode.. need to create a staw lut-dac circuit. See profiling op.")

            datasets = list(exp_profile_dataset_lib.get_datasets_by_configured_block(board, \
                                                                                         blk, \
                                                                                         cfg, \
                                                                                         hidden=False))
            unique_hidden_codes = set(map(lambda model: str(model.loc)+"." \
                                          +model.hidden_cfg, datasets))
            total_codes = args.num_hidden_codes*args.num_locs
            if len(unique_hidden_codes) >= total_codes:
                continue

            if len(datasets) > 0:
                continue_characterization(runtime, \
                                          board=board,
                                          block=blk,
                                          config=cfg, \
                                          datasets=datasets,\
                                          grid_size=args.grid_size, \
                                          num_locs=args.num_locs, \
                                          num_hidden_codes=args.num_hidden_codes
                )
            else:
                new_characterization(runtime, \
                                     board=board,
                                     block=blk,
                                     config=cfg, \
                                     grid_size=args.grid_size, \
                                     num_locs=args.num_locs, \
                                     num_hidden_codes=args.num_hidden_codes, \
                                     only_adp_locs=args.adp_locs
                )

