import sys
import os
import numpy as np
import util.paths as paths


#from compiler import  simulator
from hwlib.adp import ADP

import argparse

import compiler.legno_util as legno_util

#import conc
#import srcgen



parser = argparse.ArgumentParser(description='Legno compiler.')
parser.add_argument('--subset', default="unrestricted",
                    help='component subset to use for compilation')
parser.add_argument('--model-number',
                    help='model number of chip to use')



subparsers = parser.add_subparsers(dest='subparser_name',
                                   help='compilers/compilation passes.')

# lgraph arguments
lgraph_subp = subparsers.add_parser('lgraph', help='generate circuit')
lgraph_subp.add_argument('--vadp-fragments', type=int,default=5,
                       help='number of abs circuits to generate.')
lgraph_subp.add_argument('--vadps', type=int,default=3,
                       help='number of conc circuits to generate.')
lgraph_subp.add_argument('--adps', type=int,default=5,
                       help='maximum number of circuits to generate.')
lgraph_subp.add_argument('--asm-fragments',type=int,default=3,
                         help='number of assembly fragments that are generated')
lgraph_subp.add_argument('--synth-depth',type=int,default=20,
                         help='depth of synthesis fragments that are generated')

lgraph_subp.add_argument('program', type=str,help='benchmark to compile')

# lscale arguments
lscale_subp = subparsers.add_parser('lscale', \
                                   help='scale circuit parameters.')
lscale_subp.add_argument('--scale-method', type=str,default="ideal", \
                       help='scaling method.')
lscale_subp.add_argument('--calib-obj', type=str,default="fast", \
                       help='which calibrated block to use.')
lscale_subp.add_argument('--objective', type=str,default="qty", \
                       help='number of scaled adps to generate per adp.')
lscale_subp.add_argument('--scale-adps', type=int,default=5, \
                       help='number of scaled adps to generate per adp.')
lscale_subp.add_argument('program', type=str,help='benchmark to compile')


sim_subp = subparsers.add_parser('lsim', help='simulate circuit.')
sim_subp.add_argument('program', help='program to simulate.')

args = parser.parse_args()

#from hwlib.hcdc.hcdcv2_4 import make_board
#from hwlib.hcdc.globals import HCDCSubset
#subset = HCDCSubset(args.subset)
#hdacv2_board = make_board(subset,load_conns=True)
#args.bmark_dir = subset.value

if args.subparser_name == "lgraph":
    legno_util.exec_lgraph(args)

elif args.subparser_name == "lscale":
    legno_util.exec_lscale(args)

elif args.subparser_name == "lsim":
   legno_util.exec_lsim(args)

else:
    raise Exception("XXX")
