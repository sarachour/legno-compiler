from scripts.expdriver_db import ExpDriverDB
from scripts.common import ExecutionStatus
import lab_bench.lib.command as cmd
import lab_bench.lib.expcmd.micro_getter as microget
import lab_bench.lib.expcmd.osc as osc
import os
import time
import util.config as CONFIG
import util.util as util

def ping_user(email,entries):
    msg = ""
    with open('body.txt','w') as fh:
        for entry in entries:
            fh.write("%s\n" % entry)

    cmd = "mail -s \" %d jobs finished\" %s  <<< body.txt" \
          % (len(entries),email)

    os.system(cmd)
    os.remove('body.txt')

def execute_script(script_file, \
                   calib_obj, \
                   calibrate=False):
    print(script_file)
    if calibrate:
        calib_cmd = "python3 grendel.py calibrate {script} --calib-obj {obj}"
        cmd = calib_cmd.format(obj=calib_obj.value, \
                               script=script_file)
        os.system(cmd)

    exec_cmd = "python3 grendel.py run {script} --calib-obj {obj}"
    cmd = exec_cmd.format(obj=calib_obj.value, \
                           script=script_file)
    os.system(cmd)

def execute(args):
    from compiler.lscale_pass.scenv import LScaleEnvParams
    db = ExpDriverDB()
    entries = []
    for entry in db.experiment_tbl.get_by_status(ExecutionStatus.RAN):
        print(entry)
        entry.synchronize()

    for entry in db.experiment_tbl.get_by_status(ExecutionStatus.PENDING):
        entry.synchronize()

        if not args.prog is None and entry.program != args.prog:
            continue

        if not args.subset is None and entry.subset != args.subset:
            continue

        if not args.model is None and entry.model != args.model:
            continue

        if not args.obj is None and entry.objective_fun != args.obj:
            continue

        if entry.status == ExecutionStatus.PENDING:
            entries.append(entry)


    for entry in entries:
        fargs = util.unpack_model(entry.model)
        pars = LScaleEnvParams(model=fargs['model'], \
                               mdpe=fargs['mdpe'], \
                               mape=fargs['mape'], \
                               mc=fargs['mc'], \
                               vmape=fargs['vmape'], \
                               max_freq_khz=fargs['bandwidth_khz'])

        execute_script(entry.grendel_script, \
                       calib_obj=pars.calib_obj, \
                       calibrate=args.calibrate)
        entry.synchronize()

    if not args.email is None:
        ping_user(args.email,entries)
