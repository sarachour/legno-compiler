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

char_subp = subparsers.add_parser('characterize', help='characterize blocks fast calibraiton')
char_subp.add_argument('adp', type=str,help='adp to characterize')

calib_subp = subparsers.add_parser('cal', help='calibrate blocks in configuration')
calib_subp.add_argument('adp', type=str,help='adp to characterize')
calib_subp.add_argument('method', type=str,help='calibration objective function (minimize_error/maximize_fit)')

fastcalib_subp = subparsers.add_parser('fastcal', help='fast calibrate blocks in configuration')
fastcalib_subp.add_argument('adp', type=str,help='adp to fast-calibrate')

prof_subp = subparsers.add_parser('prof', help='characterize blocks in configuration')
prof_subp.add_argument('adp', type=str,help='adp to profile')

args = parser.parse_args()

if args.subparser_name == "exec":
    grendel_util.exec_adp(args)
elif args.subparser_name == "cal":
    grendel_util.calibrate_adp(args)
elif args.subparser_name == "fastcal":
    grendel_util.fast_calibrate_adp(args)
elif args.subparser_name == "characterize":
    grendel_util.characterize_adp(args)
else:
    raise Exception("unknown subcommand <%s>" % args.subparser_name)


