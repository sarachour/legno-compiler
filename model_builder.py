import argparse
import sys
import os
import shutil
import json
import argparse
import util.config as CONFIG
import util.util as util
from hwlib.model import ModelDB
from hwlib.hcdc.globals import HCDCSubset
from hwlib.model import PortModel, ModelDB
from hwlib.adp import AnalogDeviceProg

import compiler.infer_pass.infer_dac as infer_dac
import compiler.infer_pass.infer_adc as infer_adc
import compiler.infer_pass.infer_fanout as infer_fanout
import compiler.infer_pass.infer_integ as infer_integ
import compiler.infer_pass.infer_mult as infer_mult
import compiler.infer_pass.infer_visualize as infer_visualize
import compiler.infer_pass.infer_fit as infer_fit
import compiler.infer_pass.infer_util as infer_util



def build_model(datum):
  blk = datum['metadata']['block']
  if blk == 'dac':
    for model in infer_dac.infer(datum):
      yield model

  elif blk == 'adc':
    for model in infer_adc.infer(datum):
      yield model

  elif blk == 'fanout':
    for model in infer_fanout.infer(datum):
      yield model

  elif blk == 'integ':
    for model in infer_integ.infer(datum):
      yield model

  elif blk == 'mult':
    for model in infer_mult.infer(datum):
      yield model
  else:
    raise Exception("unsupported <%s>" % blk)

def blocks_with_default_models():
  return ['tile_in','tile_out', \
          'chip_in','chip_out', \
          'ext_chip_in','ext_chip_out',
          'ext_chip_analog_in',
          'lut']

def crossbars_populated(db,calib_obj):
  default_blocks = blocks_with_default_models()
  for model in db.get_all():
    if model.block in default_blocks and \
       model.calib_obj == calib_obj:
      return True

  return False

def populate_default_models(board,db,calib_obj):
  print("==== Populate Default Models ===")

  for blkname in blocks_with_default_models():
    block = board.block(blkname)
    for inst in board.instances_of_block(blkname):
      for port in block.inputs + block.outputs:
        model = PortModel(blkname,inst,port, \
                          comp_mode='*', \
                          scale_mode='*', \
                          calib_obj=calib_obj, \
                          handle=None)
        db.put(model)

def write_models(models):
  if len(models) == 0:
    return

  direc = infer_util.get_directory(models[0])
  filename = "model.json"
  path = "%s/%s" % (direc,filename)
  with open(path,'w') as fh:
    for model in models:
      fh.write(str(model))
      fh.write("\n\n")


def list(args):
  db = ModelDB(util.CalibrateObjective(args.calib_obj))
  for model in db.get_all():
    print(model)

def infer(args,dump_db=True):
  if args.visualize:
    infer_visualize.DO_PLOTS = True

  infer_util.CALIB_OBJ = util.CalibrateObjective(args.calib_obj)

  calib_obj=util.CalibrateObjective(args.calib_obj)
  db = ModelDB(calib_obj)

  if not crossbars_populated(db,infer_util.CALIB_OBJ):
    from hwlib.hcdc.hcdcv2_4 import make_board
    subset = HCDCSubset('unrestricted')
    hdacv2_board = make_board(subset,load_conns=False)
    populate_default_models(hdacv2_board,db,calib_obj)

  if dump_db:
    cmd = "python3 grendel.py dump"
    print(cmd)
    retcode = os.system(cmd)
    if retcode != 0:
      raise Exception("could not dump database: retcode=%d" % retcode)

  filepath = "%s/%s" % (CONFIG.DATASET_DIR,args.calib_obj)
  for dirname, subdirlist, filelist in os.walk(filepath):
    for fname in filelist:
      if fname.endswith('.json'):
        fpath = "%s/%s" % (dirname,fname)
        with open(fpath,'r') as fh:
          obj = json.loads(fh.read())
          for datum in obj:
            models = []
            for m in build_model(datum):
              if m.gain != 1.0:
                print(m)
              models.append(m)
              db.put(m)

            write_models(models)

def analyze(args):
  circ = AnalogDeviceProg.read(None,args.circ_file)
  db = ModelDB(util.CalibrateObjective(args.calib_obj))
  infer_visualize.CALIB_OBJ = util.CalibrateObjective(args.calib_obj)
  blacklist = ['tile_in','tile_out', \
               'chip_in','chip_out', \
               'ext_chip_in','ext_chip_out',
               'ext_analog_chip_in']
  for block,loc,cfg in circ.instances():
    comp_mode = cfg.comp_mode
    scale_mode = cfg.scale_mode
    if block in blacklist:
      continue

    print("===== %s[%s] cm=%s sm=%s" % (block,loc,comp_mode,scale_mode))
    has_models = False
    for model in db.get_by_block(block,loc,comp_mode,scale_mode):
      print(model)
      has_models = True

    if not has_models:
      print("...")
      print("...")
      print("NO MODELS")
      print("...")
      print("...")

parser = argparse.ArgumentParser(description="Model inference engine")

subparsers = parser.add_subparsers(dest='subparser_name',
                                   help='compilers/compilation passes.')


list_subp = subparsers.add_parser('list', \
                                   help='scale circuit parameters.')
list_subp.add_argument('--calib-obj',type=str,default='min_error',
                        help='calibration objective function to get datasets for')

infer_subp = subparsers.add_parser('infer', \
                                   help='scale circuit parameters.')
infer_subp.add_argument('--populate-crossbars',action='store_true',
                    help='insert default models for connection blocks')
infer_subp.add_argument('--disable',action='store_true',
                    help='disable blocks')
infer_subp.add_argument('--visualize',action='store_true',
                    help='emit visualizations for models')
infer_subp.add_argument('--calib-obj',type=str,
                        help='calibration objective function to get datasets for')
analyze_subp = subparsers.add_parser('analyze', \
                              help='return delta models for circuit')
analyze_subp.add_argument('circ_file',
                    help='circ file to analyze')
analyze_subp.add_argument('--calib-obj',type=str,
                        help='calibration objective function to get datasets for')

args = parser.parse_args()

if args.calib_obj is None:
  raise Exception("please specify calibration objective to infer models for")

if args.subparser_name == "list":
  list(args)

if args.subparser_name == "infer":
  infer_fit.DISABLE_BLOCKS = args.disable
  infer(args)

elif args.subparser_name == "analyze":
  analyze(args)
