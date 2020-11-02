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

args = parser.parse_args()

if args.subparser_name == "exec":
    grendel_util.exec_adp(args)
else:
    raise Exception("unknown subcommand <%s>" % args.subparser_name)


