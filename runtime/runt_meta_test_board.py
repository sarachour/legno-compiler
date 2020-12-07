from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
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


def test_source(board,adp,block,cfg):
  if block.name == "dac" and 'dyn' in str(cfg.mode):
    lut_blk = board.get_block('lut')
    dac_loc = cfg.inst.loc
    lut0_loc,lut1_loc = cfg.inst.loc.copy(), cfg.inst.loc.copy()
    lut1_loc[2] = 0 if dac_loc[2] == 2 else 2

    lut_out = list(lut_blk.outputs)[0]
    dac_in = list(block.inputs)[0]

    adp_lut0 = adp.copy(board)
    adp_lut0.add_instance(lut_blk,lut0_loc)
    adp_lut0.add_conn(lut_blk, lut0_loc, lut_out, \
                      block, dac_loc, dac_in)
    yield adp_lut0

  else:
    yield adp

def test_block(board,block,loc,modes):
  calib_objs = [
    llenums.CalibrateObjective.MAXIMIZE_FIT,
    llenums.CalibrateObjective.MINIMIZE_ERROR
  ]
  assert(not board.model_number is None)
  TMP_ADP = "tmp.adp"
  CAL_CMD = "python3 grendel.py cal {adp_path} --model-number {model_number} {calib_obj}"
  PROF_CMD = "python3 grendel.py prof {adp_path} --model-number {model_number} {calib_obj}"
  MKDELTAS_CMD = "python3 grendel.py mkdeltas --model-number {model_number}"

  for mode in modes:
    new_adp = ADP()
    new_adp.add_instance(block,loc)
    blkcfg = new_adp.configs.get(block.name,loc)
    blkcfg.modes = [mode]

    for upd_adp in test_source(board,new_adp,block,blkcfg):
      with open(TMP_ADP,'w') as fh:
        fh.write(json.dumps(upd_adp.to_json()))

      for calib_obj in calib_objs:
        for CMD in [CAL_CMD, PROF_CMD, MKDELTAS_CMD]:
          cmd = CMD.format(adp_path=TMP_ADP, \
                           model_number=board.model_number, \
                           calib_obj=calib_obj.value)
          print("############################")
          print("======== TESTING BLOCK =====");
          print("%s.%s mode=%s calib_obj=%s" \
                % (block.name,loc,mode,calib_obj.value))
          print("############################")
          print(cmd)
          code = os.system(cmd)
          print("############################")
          if code == signal.SIGINT or code != 0:
            print("status-code: %s" % code)
            raise Exception("User terminated process")


def test_board(args):
  board = runtime_util.get_device(args.model_number,layout=True)
  for chip_id in range(0,2):
    for tile_id in range(4):
      for slice_id in [0,2]:
        for block in board.blocks:
          if not block.requires_calibration():
            continue
          
          modes = list(block.modes)
          if block.name == "fanout":
            modes = list(filter(lambda m: not "-" in str(m), block.modes))

          loc = devlib.Location([chip_id,tile_id,slice_id,0])
          test_block(board,block,loc,modes)
