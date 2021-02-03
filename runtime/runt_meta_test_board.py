from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib

from lab_bench.grendel_runner import GrendelRunner
import hwlib.hcdc.llcmd_util as llutil
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd

import hwlib.device as devlib
import signal

import json
import math
import os

TESTBOARD_LOG = "testboard"

def finalize_test(board, \
                  minimize_error=False, \
                  maximize_fit=False, \
                  model_based=False):

  if model_based:
    runt_meta_util.model_based_calibration_finalize(board,TESTBOARD_LOG)


def test_block(board,block,loc,modes, \
               minimize_error=False, \
               maximize_fit=False, \
               model_based=False):

  if(board.model_number is None):
    raise Exception("please specify model number!!")


  for mode in modes:
    new_adp = ADP()
    new_adp.add_instance(block,loc)
    blkcfg = new_adp.configs.get(block.name,loc)
    blkcfg.modes = [mode]
    print("############################")
    print("======== TESTING BLOCK =====");
    print("%s.%s mode=%s" \
          % (block.name,loc,mode))
    print("############################")
    upd_adp = runtime_util.make_block_test_adp(board,new_adp,block,blkcfg)
    adp_filename = runtime_meta_util.get_adp(board,block,loc,blkcfg)

    with open(adp_filename,'w') as fh:
      fh.write(json.dumps(upd_adp.to_json()))

    if minimize_error:
      objfun = llenums.CalibrateObjective.MINIMIZE_ERROR
      runtime_meta_util.legacy_calibration(board, \
                                           adp_filename, \
                                           objfun,logfile=TESTBOARD_LOG, \
                                           block=block,mode=mode,loc=loc)


    if maximize_fit:
      objfun = llenums.CalibrateObjective.MAXIMIZE_FIT
      runtime_meta_util.legacy_calibration(board, \
                                           adp_filename, \
                                           objfun,logfile=TESTBOARD_LOG, \
                                           block=block, mode=mode, loc=loc)

    if model_based:
      runtime_meta_util.model_based_calibration(board, \
                                                adp_filename, \
                                                logfile=TESTBOARD_LOG, \
                                                block=block, mode=mode, loc=loc)

    runtime_meta_util.remove_file(adp_filename)


def test_board(args):
  board = runtime_util.get_device(args.model_number,layout=True)
  for chip_id in range(0,2):
    for tile_id in range(4):
      for slice_id in [0,2]:
        for block in board.blocks:
          if not block.requires_calibration():
            continue

          modes = list(block.modes)
          # limit the fanout modes to just positive copies
          if block.name == "fanout":
            modes = list(filter(lambda m: not "-" in str(m), block.modes))

          loc = devlib.Location([chip_id,tile_id,slice_id,0])
          test_block(board,block,loc,modes, \
                     maximize_fit=args.maximize_fit, \
                     minimize_error=args.minimize_error, \
                     model_based=args.model_based)


  finalize_test(board, \
                maximize_fit=args.maximize_fit, \
                minimize_error=args.minimize_error, \
                model_based=args.model_based)

