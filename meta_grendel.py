import sys
import os
import numpy as np
import util.paths as paths


#from compiler import  simulator
from hwlib.adp import ADP

import argparse

import runtime.runt_meta_test_board as runt_test_board
import runtime.runt_meta_characterize_bad_blocks as runt_characterize_bad_blocks
import runtime.runt_meta_bruteforce_calibrate as runt_bruteforce_cal
import runtime.runt_meta_best_calibrate as runt_best_cal
import runtime.runt_meta_dectree_calibrate as runt_dectree_cal

parser = argparse.ArgumentParser(description='Meta-grendel routines.')

subparsers = parser.add_subparsers(dest='subparser_name',
                                   help='compilers/compilation passes.')


exec_subp = subparsers.add_parser('test_board', help='test the board at hand')
exec_subp.add_argument('model_number', type=str,help='model of board to test')

exec_subp = subparsers.add_parser('char_bad_blocks', help='characterize badly calibrated blocks in database')
exec_subp.add_argument('model_number', type=str,help='model of board to test')
exec_subp.add_argument('--dry',action='store_true',help='dry run')
exec_subp.add_argument('--cutoff',default=5.0, type=float, help='percent error cutoff for bad blocks')

exec_subp = subparsers.add_parser('best_cal', help='bruteforce calibration for all individually characterized blocks')
exec_subp.add_argument('model_number', type=str,help='model of board to study')


exec_subp = subparsers.add_parser('bruteforce_cal', help='bruteforce calibration for all individually characterized blocks')
exec_subp.add_argument('model_number', type=str,help='model of board to study')

exec_subp = subparsers.add_parser('dectree_cal', help='dectree calibration for all individually characterized blocks')
exec_subp.add_argument('model_number', type=str,help='model of board study')
args = parser.parse_args()

if args.subparser_name == "test_board":
    runt_test_board.test_board(args)
elif args.subparser_name == "char_bad_blocks":
    runt_characterize_bad_blocks.characterize_bad_blocks(args)
elif args.subparser_name == "bruteforce_cal":
    runt_bruteforce_cal.calibrate(args)
elif args.subparser_name == "best_cal":
    runt_best_cal.calibrate(args)
elif args.subparser_name == "dectree_cal":
    runt_dectree_cal.calibrate(args)
else:
    raise Exception("unhandled: %s" % args.subparser_name)


