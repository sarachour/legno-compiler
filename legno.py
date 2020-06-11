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


subparsers = parser.add_subparsers(dest='subparser_name',
                                   help='compilers/compilation passes.')

lgraph_subp = subparsers.add_parser('lgraph', help='generate circuit')
lgraph_subp.add_argument('--simulate', action="store_true",
                       help="ignore resource constraints while compiling.")
lgraph_subp.add_argument('--xforms', type=int,default=3,
                       help='number of abs circuits to generate.')
lgraph_subp.add_argument('--vadp-fragments', type=int,default=100,
                       help='number of abs circuits to generate.')
lgraph_subp.add_argument('--vadps', type=int,default=3,
                       help='number of conc circuits to generate.')
lgraph_subp.add_argument('--adps', type=int,default=5,
                       help='maximum number of circuits to generate.')


lgraph_subp.add_argument('program', type=str,help='benchmark to compile')

lscale_subp = subparsers.add_parser('lscale', \
                                   help='scale circuit parameters.')
lscale_subp.add_argument('--model', default="naive-min_error",
                        help='use physical models to inform constraints.')
lscale_subp.add_argument('--ignore-model',action='append',
                         help='don\'t use delta models for a specific type of block')
lscale_subp.add_argument('--ignore-missing', action="store_true", \
                         help='ignore missing delta models')
lscale_subp.add_argument('--scale-circuits', type=int,default=5, \
                       help='number of scaled circuits to generate.')
lscale_subp.add_argument('--mc', type=float, default=0.80, \
                        help='minimum coverage for digital signals.')
lscale_subp.add_argument('--mdpe', type=float, default=0.04, \
                        help='maximum digital percent error.')
lscale_subp.add_argument('--mape',type=float,default=0.04, \
                        help='maximum analog percent error.')
lscale_subp.add_argument('--search',action="store_true")
lscale_subp.add_argument('program', type=str,help='benchmark to compile')

lscale_subp.add_argument("--max-freq", type=float, \
                         help="maximum frequency in Khz")

graph_subp = subparsers.add_parser('graph', \
                                   help='emit debugging graph.')
graph_subp.add_argument('--circ', type=str, \
                        help='do performance sweep.')


gren_subp = subparsers.add_parser('srcgen', help='generate grendel script.')
gren_subp.add_argument('--hwenv', type=str, \
                        help='hardware environment')
gren_subp.add_argument('--recompute', action='store_true',
                       help='recompute.')
gren_subp.add_argument('--trials', type=int, default=1,
                       help='compute trials.')
gren_subp.add_argument('program', type=str,help='benchmark to compile')


sim_subp = subparsers.add_parser('simulate', help='simulate circuit.')
sim_subp.add_argument('program', help='program to simulate.')
sim_subp.add_argument('--adp',help='analog device program to simulate')
sim_subp.add_argument('--runtime',action="store_true", \
        help='only measure runtime performance')
sim_subp.add_argument('--reference',action="store_true", \
                      help='execute reference simulation')
sim_subp.add_argument("--mode",default="naive-min_error",
                      help='should the simulator use delta models / which ones')
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

elif args.subparser_name == "srcgen":
   legno_util.exec_srcgen(args)

elif args.subparser_name == "graph":
   legno_util.exec_graph(args)

elif args.subparser_name == "simulate":
   simulator.simulate(args)
