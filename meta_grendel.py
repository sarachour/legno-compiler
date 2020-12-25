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
import runtime.runt_meta_model_calibrate as runt_model_cal

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



'''
exec_subp = subparsers.add_parser('char_bad_blocks', help='characterize badly calibrated blocks in database')
exec_subp.add_argument('model_number', type=str,help='model of board to test')
exec_subp.add_argument('--dry',action='store_true',help='dry run')
exec_subp.add_argument('--cutoff',default=5.0, type=float, help='percent error cutoff for bad blocks')
'''

best_subp = subparsers.add_parser('best_cal', help='bruteforce calibration for all individually characterized blocks')
best_subp.add_argument('model_number', type=str,help='model of board to study')


mdl_subp = subparsers.add_parser('model_cal', help='linear model calibration for all individually characterized blocks')
mdl_subp.add_argument('model_number', type=str,help='model of board to study')
mdl_subp.add_argument('--grid-size',default=7,type=int,help='size of grid to profile.')
mdl_subp.add_argument('--candidate-samples',default=3,type=int, \
                      help='number of candidate hidden codes per iteration.')
mdl_subp.add_argument('--bootstrap-samples',default=5,type=int,help='number of bootstrapping samples.')
mdl_subp.add_argument('--num-iters',default=3,type=int,help='number of iterations.')
mdl_subp.add_argument('--adp',type=str,help='adp to calibrate.')
mdl_subp.add_argument('--widen',action='store_true',help='widen the set of modes.')
mdl_subp.add_argument('--cutoff', type=float, \
                      help='score cutoff to terminate')



brute_subp = subparsers.add_parser('bruteforce_cal', \
                                   help='bruteforce calibration for all individually characterized blocks')
brute_subp.add_argument('model_number', type=str,help='model of board to study')

args = parser.parse_args()

if args.subparser_name == "test_board":
    runt_test_board.test_board(args)
elif args.subparser_name == "char_bad_blocks":
    runt_characterize_bad_blocks.characterize_bad_blocks(args)
elif args.subparser_name == "bruteforce_cal":
    runt_bruteforce_cal.calibrate(args)
elif args.subparser_name == "best_cal":
    runt_best_cal.calibrate(args)
elif args.subparser_name == "model_cal":
    runt_model_cal.calibrate(args)
else:
    raise Exception("unhandled: %s" % args.subparser_name)


