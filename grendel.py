import sys
import os
import numpy as np
import util.paths as paths


#from compiler import  simulator
from hwlib.adp import ADP

import argparse

import runtime.runtime_util as grendel_util


parser = argparse.ArgumentParser(description='Grendel runtime.')

subparsers = parser.add_subparsers(dest='subparser_name',
                                   help='compilers/compilation passes.')


exec_subp = subparsers.add_parser('exec', help='execute benchmark')
exec_subp.add_argument('adp', type=str,help='benchmark to compile')
exec_subp.add_argument('--runtime',type=float,help='runtime in simulation units')

char_subp = subparsers.add_parser('characterize', help='characterize blocks for fast calibration. This takes a really long time')
char_subp.add_argument('adp', type=str,help='adp to characterize')
char_subp.add_argument('--model-number',type=str,help='model number')
char_subp.add_argument('--grid-size',type=int,default=7, \
                       help="number of inputs to sample along each axis")
char_subp.add_argument('--num-hidden-codes',type=int,default=20, \
                       help="number of hidden codes to sample")
char_subp.add_argument('--num-locs',type=int,default=2, \
                       help="number of hidden codes to sample")



char_subp = subparsers.add_parser('fastcal_srcgen', help='generate c sources for fast calibration routine')

dectree_subp = subparsers.add_parser('mktree', help='Use characterization data to build calibration decision tree.')
dectree_subp.add_argument('adp', type=str,help='adp to characterize')
dectree_subp.add_argument('--model-number',type=str,help='model number')
dectree_subp.add_argument('--max-depth',type=int,default=3,\
                          help='maximum depth')
dectree_subp.add_argument('--num-leaves',type=int,default=10,\
                          help='number of leaves')



fastcal_subp = subparsers.add_parser('fastcal', help='fastcalrate blocks in configuration')
fastcal_subp.add_argument('adp', type=str,help='adp to characterize')
fastcal_subp.add_argument('method', type=str,help='fast calibration objective function (minimize_error/maximize_fit)')
fastcal_subp.add_argument('--model-number',type=str,help='model number')
fastcal_subp.add_argument('--on-firmware',type=str,help='execute fast calibration routine resident on firmware')



calib_subp = subparsers.add_parser('cal', help='calibrate blocks in configuration')
calib_subp.add_argument('adp', type=str,help='adp to characterize')
calib_subp.add_argument('method', type=str,help='calibration objective function (minimize_error/maximize_fit)')
calib_subp.add_argument('--model-number',type=str,help='model number')

fastcalib_subp = subparsers.add_parser('fastcal', help='fast calibrate blocks in configuration')
fastcalib_subp.add_argument('adp', type=str,help='adp to fast-calibrate')


prof_subp = subparsers.add_parser('prof', help='profile calibrated blocks')
prof_subp.add_argument('adp', type=str,help='adp to profile')
prof_subp.add_argument('method', type=str,help='delta label to profile (legacy_min_error/legacy_max_fit/min_error/max_fit)')
prof_subp.add_argument('--model-number',type=str,help='model number')
prof_subp.add_argument('--grid-size',type=int,default=5, \
                       help="number of inputs to sample along each axis")
prof_subp.add_argument('--max-points',type=int,default=50, \
                       help="maximum number of dataset points")


delta_subp = subparsers.add_parser('delta', help='build delta models from profile information')
delta_subp.add_argument('adp', type=str,help='adp to profile')
delta_subp.add_argument('--model-number',type=str,help='model number')
delta_subp.add_argument('--min-points',default=10,help='minimum number of points to fit model')
args = parser.parse_args()

if args.subparser_name == "exec":
    grendel_util.exec_adp(args)
elif args.subparser_name == "cal":
    grendel_util.calibrate_adp(args)
elif args.subparser_name == "prof":
    grendel_util.profile_adp(args)
elif args.subparser_name == "delta":
    grendel_util.derive_delta_models_adp(args)
elif args.subparser_name == "fastcal":
    grendel_util.fast_calibrate_adp(args)
elif args.subparser_name == "characterize":
    grendel_util.characterize_adp(args)
elif args.subparser_name == "mktree":
    grendel_util.mktree_adp(args)
else:
    raise Exception("unknown subcommand <%s>" % args.subparser_name)


