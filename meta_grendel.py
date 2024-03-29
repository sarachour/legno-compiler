import sys
import os
import numpy as np
import util.paths as paths


#from compiler import  simulator
from hwlib.adp import ADP

import argparse

import runtime.runt_meta_test_board as runt_test_board
import runtime.runt_meta_best_calibrate as runt_best_cal
import runtime.runt_meta_active_calibrate as runt_active_cal

parser = argparse.ArgumentParser(description='Meta-grendel routines.')

subparsers = parser.add_subparsers(dest='subparser_name',
                                   help='compilers/compilation passes.')


testboard_subp = subparsers.add_parser('test_board', help='test the board at hand')
testboard_subp.add_argument('model_number', type=str,help='model of board to test')
testboard_subp.add_argument('--maximize-fit',action='store_true', \
                            help='run legacy maximize fit calibration routine.')
testboard_subp.add_argument('--minimize-error',action='store_true', \
                            help='run legacy minimize error calibration routine.')

testboard_subp.add_argument('--model-based',action='store_true', \
                            help='run model-based calibration routine.')

best_subp = subparsers.add_parser('best_cal', help='bruteforce calibration for all individually characterized blocks')
best_subp.add_argument('model_number', type=str,help='model of board to study')


mdl_subp = subparsers.add_parser('active_cal', help='active learning based calibration with transferrable model')
mdl_subp.add_argument('model_number', type=str,help='model of board to study')
mdl_subp.add_argument('--xfer-db', type=str,help='database with physical models for transfer learning')
mdl_subp.add_argument('--grid-size',default=25,type=int,help='size of grid to profile.')
mdl_subp.add_argument('--samples-per-round',default=3,type=int, \
                      help='number of candidate hidden codes per iteration.')
mdl_subp.add_argument('--rounds',default=3,type=int,help='number of iterations.')
mdl_subp.add_argument('--max-samples',default=20,type=int,help='max number of samples.')
mdl_subp.add_argument('--adp',type=str,help='adp to calibrate.')
mdl_subp.add_argument('--widen',action='store_true',help='widen the set of modes.')

args = parser.parse_args()

if args.subparser_name == "test_board":
    runt_test_board.test_board(args)
elif args.subparser_name == "char_bad_blocks":
    runt_characterize_bad_blocks.characterize_bad_blocks(args)
elif args.subparser_name == "best_cal":
    runt_best_cal.calibrate(args)
elif args.subparser_name == "active_cal":
    runt_active_cal.calibrate(args)
else:
    raise Exception("unhandled: %s" % args.subparser_name)


