import sys
import os
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
lgraph_subp.add_argument('--routes', type=int,default=3,
                       help='number routed circuits to generate.')
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
lscale_subp.add_argument('program', type=str,help='benchmark to compile')
lscale_subp.add_argument('--scale-method', type=str,default="ideal", \
                       help='scaling method.')
lscale_subp.add_argument('--calib-obj', type=str,default="minimize_error", \
                       help='which calibrated block to use.')
lscale_subp.add_argument('--objective', type=str,default="qty", \
                       help='number of scaled adps to generate per adp.')
lscale_subp.add_argument('--model-number', type=str, \
                       help='identifier for board.')
lscale_subp.add_argument('--scale-adps', type=int,default=5, \
                       help='number of scaled adps to generate per adp.')
lscale_subp.add_argument('--min-aqm', type=float, \
                       help='minimum aqm.')
lscale_subp.add_argument('--min-dqm', type=float, \
                       help='minimum dqm.')
lscale_subp.add_argument('--min-dqme', type=float, \
                       help='minimum dqme.')
lscale_subp.add_argument('--min-tau', type=float, \
                       help='minimum tau.')
lscale_subp.add_argument('--one-mode',action="store_true", \
                         help="only use the medium mode")
lscale_subp.add_argument('--no-scale',action="store_true", \
                         help="don't scale the circuit")



lcal_subp = subparsers.add_parser('lcal', help='execute circuit using grendel.')
lcal_subp.add_argument('program', help='program to execute.')
lcal_subp.add_argument('--model-number', type=str, \
                       help='identifier for board.')
lcal_subp.add_argument('--minimize-error', action='store_true', \
                       help='calibrate with error minimization strategy.')
lcal_subp.add_argument('--maximize-fit', action='store_true', \
                       help='calibrate with maximize fit strategy.')
lcal_subp.add_argument('--model-based', action='store_true', \
                       help='calibrate with model-based strategy.')




lexec_subp = subparsers.add_parser('lexec', help='execute circuit using grendel.')
lexec_subp.add_argument('program', help='program to execute.')
lexec_subp.add_argument('--force', action='store_true', \
                       help='force reexecution.')
lexec_subp.add_argument('--scope', action='store_true', \
                       help='also measure waveform with sigilent oscilloscope.')

sim_subp = subparsers.add_parser('lsim', help='simulate circuit.')
sim_subp.add_argument('program', help='program to simulate.')
sim_subp.add_argument('--separate-figures', action='store_true', \
                       help='separate figures.')



emul_subp = subparsers.add_parser('lemul', help='simulate circuit.')
emul_subp.add_argument('program', help='program to simulate.')
emul_subp.add_argument('--unscaled', action='store_true', \
                       help='simulate unscaled circuit.')
emul_subp.add_argument('--no-quantize', action='store_true', \
                       help='don\'t quantize values.')
emul_subp.add_argument('--no-operating-range', action='store_true', \
                       help='don\'t enforce operating range.')
emul_subp.add_argument('--no-physdb', action='store_true', \
                       help='disable physical database.')
emul_subp.add_argument('--no-model-error', action='store_true', \
                       help='disable physical database.')
emul_subp.add_argument('--separate-figures', action='store_true', \
                       help='separate figures.')



rend_subp = subparsers.add_parser('lrender', help='re-render circuit diagrams.')
rend_subp.add_argument('program', help='program to analyze.')

plot_subp = subparsers.add_parser('lstats', help='analyze waveforms.')
plot_subp.add_argument('program', help='program to analyze.')
plot_subp.add_argument('--equations', action='store_true', \
                       help='print signal equation latex formulas.')
plot_subp.add_argument('--performance', action='store_true', \
                       help='print energy/power/runtime/quality summary.')
plot_subp.add_argument('--compile-times', action='store_true', \
                       help='print performance summary.')



plot_subp.add_argument('--lgraph-rmse-plots', action='store_true', \
                       help='plot rmse breakdown by lgraph circuit.')
plot_subp.add_argument('--lgraph-static', action='store_true', \
                       help='print out block breakdown.')


plot_subp.add_argument('--lscale-static', action='store_true', \
                       help='print quality measure and scale transform breakdown.')
plot_subp.add_argument('--lscale-correlation', action='store_true', \
                       help='print out quality measure + signal correlations to rmse.')
plot_subp.add_argument('--lscale-top5', action='store_true', \
                       help='print top 5 circuits.')
plot_subp.add_argument('--lscale-delta-model-plots', action='store_true', \
                       help='plot delta model compensation plots.')
plot_subp.add_argument('--lscale-scale-objective-plots', action='store_true', \
                       help='plot scale objective plots.')






plot_subp = subparsers.add_parser('lwav', help='analyze waveforms.')
plot_subp.add_argument('program', help='program to analyze.')
plot_subp.add_argument('--summary-plots', action='store_true', \
                       help='generate summary plots.')
plot_subp.add_argument('--individual-plots', action='store_true', \
                       help='generate summary plots.')
plot_subp.add_argument('--emulate', action='store_true', \
                       help='compare to emulated result.')
plot_subp.add_argument('--scope-only', action='store_true', \
                       help='only plot waveforms collected from the oscilloscope.')
plot_subp.add_argument('--adc-only', action='store_true', \
                       help='only plot waveforms collected from the oscilloscope.')

plot_subp.add_argument('--measured', action='store_true', \
                       help='plot measured waveform.')






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

elif args.subparser_name == "lexec":
   legno_util.exec_lexec(args)

elif args.subparser_name == "lcal":
   legno_util.exec_lcal(args)

elif args.subparser_name == "lsim":
   legno_util.exec_lsim(args)

elif args.subparser_name == "lemul":
   legno_util.exec_lemul(args)


elif args.subparser_name == "lwav":
   legno_util.exec_wav(args)

elif args.subparser_name == "lstats":
   legno_util.exec_stats(args)

elif args.subparser_name == "lrender":
   legno_util.exec_render(args)



else:
    raise Exception("legno.py: unknown subcommand: <%s>" % args.subparser_name)
