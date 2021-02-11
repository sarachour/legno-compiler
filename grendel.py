import sys
import os
import numpy as np
import util.paths as paths


#from compiler import  simulator
from hwlib.adp import ADP

import argparse

import runtime.runt_characterize as runt_char
import runtime.runt_calibrate as runt_cal
import runtime.runt_fastcal as runt_fastcal
import runtime.runt_execute as runt_exec
import runtime.runt_profile as runt_prof
import runtime.runt_visualize as runt_visualize
import runtime.runt_mkdeltamodels as runt_mkdeltas
import runtime.runt_mkphysmodels as runt_mkphys
import runtime.runt_clear as runt_clear


parser = argparse.ArgumentParser(description='Grendel runtime.')

subparsers = parser.add_subparsers(dest='subparser_name',
                                   help='runtime tools.')


exec_subp = subparsers.add_parser('exec', help='execute benchmark')
exec_subp.add_argument('adp', type=str,help='benchmark to compile')
exec_subp.add_argument('--runtime',type=float,help='runtime in simulation units')
exec_subp.add_argument('--model-number',type=str,help='model database to use')
exec_subp.add_argument('--osc',action='store_true',help='oscilloscope connected')

testosc_subp = subparsers.add_parser('test_osc', help='test the oscilloscope')
testosc_subp.add_argument('adp', type=str,help='benchmark to compile')
testosc_subp.add_argument('--runtime',type=float,help='runtime in simulation units')
testosc_subp.add_argument('--model-number',type=str,help='model database to use')
testosc_subp.add_argument('--no-osc',action='store_true',help='no oscilloscope connected')

char_subp = subparsers.add_parser('characterize', help='characterize blocks for fast calibration. This takes a really long time')
char_subp.add_argument('adp', type=str,help='adp to characterize')
char_subp.add_argument('--model-number',type=str,help='model number')
char_subp.add_argument('--grid-size',type=int,default=7, \
                       help="number of inputs to sample along each axis")
char_subp.add_argument('--num-hidden-codes',type=int,default=200, \
                       help="number of hidden codes to sample")
char_subp.add_argument('--num-locs',type=int,default=1, \
                       help="number of hidden codes to sample")
char_subp.add_argument('--adp-locs',action='store_true', \
                       help="only characterize the locations which appear in the adp")
char_subp.add_argument('--widen',action='store_true', \
                       help="widen adp modes to all modes which introduce constant coefficients")



dectree_subp = subparsers.add_parser('mkphys', help='Use characterization data to build calibration decision tree.')
dectree_subp.add_argument('--model-number',type=str,help='model number')
#dectree_subp.add_argument('--max-depth',type=int,default=2,\
#                          help='maximum depth (default=2)')
#dectree_subp.add_argument('--num-leaves',type=int,default=3,\
#                          help='number of leaves (default=3)')
#dectree_subp.add_argument('--shrink',action='store_true', help='shrink model')
dectree_subp.add_argument('--local-model',action='store_true', help='only model points around local minima')
dectree_subp.add_argument('--num-points',type=int, help='number points to use for local model')




calib_subp = subparsers.add_parser('cal', help='calibrate blocks in configuration')
calib_subp.add_argument('adp', type=str,help='adp to characterize')
calib_subp.add_argument('method', type=str,help='calibration objective function (minimize_error/maximize_fit)')
calib_subp.add_argument('--model-number',type=str,help='model number')
calib_subp.add_argument('--widen',action="store_true",help='widen modes')


clear_subp = subparsers.add_parser('clear', help='clear data')
clear_subp.add_argument('--profiles',action="store_true",help='clear profiling data')
clear_subp.add_argument('model_number',action="store_true",help='board model')

prof_subp = subparsers.add_parser('prof', help='profile calibrated blocks')
prof_subp.add_argument('adp', type=str,help='adp to profile')
prof_subp.add_argument('method', type=str, \
                       default='none', \
                       help='delta label to profile (/minimize_error/maximize_fit/best/dectree)')
prof_subp.add_argument('--model-number',type=str,help='model number')
prof_subp.add_argument('--grid-size',type=int,default=15, \
                       help="number of inputs to sample along each axis")
prof_subp.add_argument('--max-points',type=int,default=255, \
                       help="maximum number of points to sample")
prof_subp.add_argument('--min-points',type=int,default=0, \
                       help="minimum number of dataset points")
prof_subp.add_argument('--missing',action='store_true', \
                       help="calibrate missing")
prof_subp.add_argument('--force',action="store_true",help='force')
prof_subp.add_argument('--widen',action="store_true",help='widen modes')



vis_subp = subparsers.add_parser('vis', help='build delta model visualizations')
vis_subp.add_argument('calib_obj', type=str, \
                       help='vis label to profile (none/maximize_fit/minimize_error/brute)')
vis_subp.add_argument('--model-number',type=str,help='model number')
vis_subp.add_argument('--histogram',action="store_true",help='render error histograms')
vis_subp.add_argument('--absolute',action="store_true",help='absolute error')
vis_subp.add_argument('--max-error',type=float, \
                      help='max error')


delta_subp = subparsers.add_parser('mkdeltas', help='build delta models from profile information')
delta_subp.add_argument('--model-number',type=str,help='model number')
delta_subp.add_argument('--force',action="store_true",help='force')
delta_subp.add_argument('--no-orphans',action="store_true",help='don\'t add models that don\'t already exist')
delta_subp.add_argument('--min-points',default=10,help='minimum number of points to fit model')
args = parser.parse_args()

if args.subparser_name == "exec":
    runt_exec.exec_adp(args)
elif args.subparser_name == "test_osc":
    runt_exec.test_osc(args)
elif args.subparser_name == "cal":
    runt_cal.calibrate_adp(args)
elif args.subparser_name == "prof":
    runt_prof.profile_adp(args)
elif args.subparser_name == "clear":
    runt_clear.clear(args)
elif args.subparser_name == "mkdeltas":
    runt_mkdeltas.derive_delta_models_adp(args)
elif args.subparser_name == "fastcal":
    runt_fastcal.fast_calibrate_adp(args)
elif args.subparser_name == "characterize":
    runt_char.characterize_adp(args)
elif args.subparser_name == "mkphys":
    runt_mkphys.mktree(args)
elif args.subparser_name == "vis":
    runt_visualize.visualize(args)
else:
    raise Exception("unknown subcommand <%s>" % args.subparser_name)


