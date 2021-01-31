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

def get_config(block,mode):
  return {
    'bootstrap_samples': 15,
    'candidate_samples':3,
    'num_iters': 18,
    'grid_size': 7,
    'cutoff':runtime_meta_util.get_tolerance(block,mode)
  }

def legacy_calibration(board,adp_path,block,mode,calib_obj):
  CAL_CMD = 'cal',"python3 grendel.py cal {adp_path} --model-number {model_number} {calib_obj}"
  PROF_CMD = 'prof',"python3 grendel.py prof {adp_path} --model-number {model_number} {calib_obj}"
  MKDELTAS_CMD = 'deltas',"python3 grendel.py mkdeltas --model-number {model_number}"


  cmds = []
  for label,CMD in [CAL_CMD, PROF_CMD, MKDELTAS_CMD]:
    cmd = CMD.format(adp_path=adp_path, \
                     model_number=board.model_number, \
                     calib_obj=calib_obj.value)
    cmds.append((label,cmd))

  return cmds

def model_based_calibration(board,adp_path,block,mode):
  CAL_CMD = "python3 meta_grendel.py model_cal {model_number} --adp {adp_path}"
  CAL_CMD += " --bootstrap-samples {bootstrap_samples}"
  CAL_CMD += " --candidate-samples {candidate_samples}"
  CAL_CMD += " --num-iters {num_iters}"
  CAL_CMD += " --grid-size {grid_size}"
  CAL_CMD += " --default-cutoff"

  cmds = []
  cfg = get_config(block,mode)
  cfg['model_number'] = board.model_number
  cfg['adp_path'] = adp_path
  cmds.append(('model_cal', CAL_CMD.format(**cfg)))

  #BRCAL_CMD = "python3 meta_grendel.py bruteforce_cal {model_number}"
  #cmds.append(('brute_cal',BRCAL_CMD.format(model_number=board.model_number)))

  return cmds

def test_block(board,block,loc,modes, \
               minimize_error=False, \
               maximize_fit=False, \
               model_based=False):

  if(board.model_number is None):
    raise Exception("please specify model number!!")

  fields = ['block','loc','mode','calib_obj','operation','runtime']
  logger = runtime_meta_util.Logger('testboard_%s.log' % board.model_number, \
                                    fields)

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
      cmds = legacy_calibration(board,adp_file,block,mode,objfun)
      for name,cmd in cmds:
        print(cmd)
        runtime = runtime_meta_util.run_command(cmd)
        logger.log(block=block.name, loc=str(loc), mode=str(mode), \
                    calib_obj=objfun.value, operation=name, runtime=runtime)



    if maximize_fit:
      objfun = llenums.CalibrateObjective.MAXIMIZE_FIT
      cmds = legacy_calibration(board,adp_file,block,mode, objfun)
      for name,cmd in cmds:
        print(cmd)
        runtime = runtime_meta_util.run_command(cmd)
        logger.log(block=block.name, loc=str(loc), mode=str(mode), \
                    calib_obj=objfun.value, operation=name, runtime=runtime)


    if model_based:
      cmds = model_based_calibration(board,adp_filename,block,mode)
      for name,cmd in cmds:
        print(cmd)
        runtime = runtime_meta_util.run_command(cmd)
        logger.log(block=block.name, loc=str(loc), mode=str(mode), \
                    calib_obj='model',operation=name, runtime=runtime)


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
          if block.name == "fanout":
            modes = list(filter(lambda m: not "-" in str(m), block.modes))

          loc = devlib.Location([chip_id,tile_id,slice_id,0])
          test_block(board,block,loc,modes, \
                     maximize_fit=args.maximize_fit, \
                     minimize_error=args.minimize_error, \
                     model_based=args.model_based)
