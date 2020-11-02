import argparse
import sys
import os
import util.config as CONFIG
import util.util as util
#sys.path.insert(0,os.path.abspath("."))

from lab_bench.lib.command_handler import main_stdout,  \
    main_script, \
    main_script_calibrate, \
    main_script_profile, \
    main_dump_db
from lab_bench.lib.base_command import ArduinoCommand
from lab_bench.lib.env import GrendelEnv
import lab_bench.lib.gen_script as gen_script

def add_args(parser):
    parser.add_argument("--native", action='store_true', \
                        help="use native mode for arduino DUE.")
    parser.add_argument("--debug", action='store_true', \
                        help="use debug mode on arduino DUE.")
    parser.add_argument("--validate", action='store_true', \
                        help="don't dispatch commands to arduino DUE.")
    parser.add_argument("--calib-obj", type=str, \
                        help="what optimization function to use for calibration")
    parser.add_argument("--no-oscilloscope", action='store_true', \
                        help="use native mode for arduino DUE.")
    parser.add_argument("--ip", type=str, help="ip address of oscilloscope.")
    parser.add_argument("--port", type=int, default=5024, \
                        help="port number of oscilloscope.")

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='subparser_name',
                                   help='compilers/compilation passes.')

import_subp = subparsers.add_parser('import', \
                                    help='import database')
import_subp.add_argument("filename", type=str, \
                         help="filename to import state objects from")


export_subp = subparsers.add_parser('export', \
                                   help='export database')
export_subp.add_argument("filename", type=str, \
                       help="filename to export state objects to")


genscript_subp = subparsers.add_parser('gen-script', \
                                   help='generate a script for recalibrating all components in the grendel database.')
genscript_subp.add_argument("filename", type=str, \
                       help="filename to export state objects to")
genscript_subp.add_argument("--calib-obj", type=str, \
                       help="what optimization function to use for calibration")



dump_subp = subparsers.add_parser('dump', \
                                   help='dump database to datasets')
dump_subp.add_argument("--calib-obj", type=str, \
                       help="what optimization function to use for calibration")


run_subp = subparsers.add_parser('run', \
                                   help='execute script')
run_subp.add_argument("script", type=str, \
                    help="read data using script.")
add_args(run_subp)

calib_subp = subparsers.add_parser('calibrate', \
                                   help='calibrate blocks in script')
calib_subp.add_argument("--recompute", action='store_true', \
                    help="recompute calibration codes")
calib_subp.add_argument("script", type=str, \
                    help="read data using script.")
add_args(calib_subp)

prof_subp = subparsers.add_parser('profile', \
                                   help='profile blocks in script')
prof_subp.add_argument("--profile", action='store_true', \
                    help="profile components on chip")
prof_subp.add_argument("--clear-profile", action='store_true', \
                    help="clear profiles on chip")
prof_subp.add_argument("script", type=str, \
                    help="read data using script.")
add_args(prof_subp)


args = parser.parse_args()

if args.subparser_name == "gen-script":
    state = GrendelEnv(None,None, \
                       ard_native=False, \
                       calib_obj=util.CalibrateObjective(args.calib_obj))
    gen_script.generate(state.state_db,args.filename)
    sys.exit(0)


if args.subparser_name == "import":
    state = GrendelEnv(None,None, \
                       ard_native=False, \
                       calib_obj=util.CalibrateObjective.MIN_ERROR)
    state.state_db.load(args.filename)
    sys.exit(0)


if args.subparser_name == "export":
    state = GrendelEnv(None,None, \
                       ard_native=False, \
                       calib_obj=util.CalibrateObjective.MIN_ERROR)
    state.state_db.export(args.filename)
    sys.exit(0)

# Dump database and quit
if args.subparser_name == "dump":
    state = GrendelEnv(None,None, \
                       ard_native=False, \
                       calib_obj=args.calib_obj)
    main_dump_db(state)
    sys.exit(0)

if args.calib_obj is None:
    raise Exception("please specify calibration objective (max_fit|min_error)")

if args.debug:
    ArduinoCommand.set_debug(True)
else:
    ArduinoCommand.set_debug(False)

ip = args.ip
if args.ip is None and not args.no_oscilloscope:
    ip = CONFIG.OSC_IP
elif args.no_oscilloscope:
    ip = None

state = GrendelEnv(ip,args.port,
                   ard_native=args.native,
                   validate=args.validate,
                   calib_obj=util.CalibrateObjective(args.calib_obj))

state.initialize()

if args.subparser_name == "calibrate":
    assert(args.script != None)
    succ = main_script_calibrate(state,args.script, \
                                 recompute=args.recompute,
                                 calib_obj=state.calib_obj)
    sys.exit(0)

elif args.subparser_name == "profile":
    succ = main_script_profile(state,args.script, \
                               clear=args.clear_profile)

elif args.subparser_name == "run":
    try:
        if args.script == None:
            main_stdout(state)
        else:
            main_script(state,args.script)

    except Exception as e:
        print("<< closing devices >>")
        state.close()
        raise e

