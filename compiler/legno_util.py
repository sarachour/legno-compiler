#from compiler import lgraph, lscale, srcgen, execprog
import os
import time
import json
import shutil
import numpy as np
import itertools
import util.util as util
import util.paths as paths
from hwlib.adp import ADP,ADPMetadata
from dslang.dsprog import DSProgDB
import json
import hwlib.adp_renderer as adprender
import hwlib.hcdc.llenums as llenums

def get_device(model_number):
    import hwlib.hcdc.hcdcv2 as hcdclib
    return hcdclib.get_device(model_number,layout=True)

def get_calibrate_objective(name):
    return llenums.CalibrateObjective(name)

def exec_lscale(args):
    from compiler import lscale
    import compiler.lscale_pass.lscale_ops as scalelib

    board = get_device(args.model_number)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    timer = util.Timer('lscale',path_handler)
    for dirname, subdirlist, filelist in \
        os.walk(path_handler.lgraph_adp_dir()):
        for lgraph_adp_file in filelist:
            if lgraph_adp_file.endswith('.adp'):
                with open(dirname+"/"+lgraph_adp_file,'r') as fh:
                    print("===== %s =====" % (lgraph_adp_file))
                    adp = ADP.from_json(board, \
                                        json.loads(fh.read()))


                obj = scalelib.ObjectiveFun(args.objective)
                scale_method = scalelib.ScaleMethod(args.scale_method)
                calib_obj = get_calibrate_objective(args.calib_obj)
                for idx,scale_adp in enumerate(lscale.scale(board, \
                                                            program, \
                                                            adp, \
                                                            objective=obj, \
                                                            scale_method=scale_method, \
                                                            calib_obj=calib_obj)):

                    print("<<< writing scaled circuit %d/%d>>>" % (idx,args.scale_adps))
                    scale_adp.metadata.set(ADPMetadata.Keys.LSCALE_ID,idx)

                    calib_tag = llenums.CalibrateObjective(scale_adp \
                                                       .metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ]).tag()
                    filename = path_handler.lscale_adp_file(
                        scale_adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                        scale_adp.metadata[ADPMetadata.Keys.LSCALE_ID],
                        scale_adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                        scale_adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE],
                        calib_tag,
                        scale_adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB]
                    )

                    with open(filename,'w') as fh:
                        jsondata = scale_adp.to_json()
                        fh.write(json.dumps(jsondata,indent=4))

                    print("<<< writing graph >>>")
                    filename = path_handler.lscale_adp_diagram_file(
                        scale_adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                        scale_adp.metadata[ADPMetadata.Keys.LSCALE_ID],
                        scale_adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                        scale_adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE],
                        calib_tag,
                        scale_adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB]
                    )

                    adprender.render(board,scale_adp,filename)
                    if idx >= args.scale_adps:
                        break
                    timer.start()


    print("<<< done >>>")
    timer.kill()
    print(timer)
    timer.save()


def exec_lgraph(args):
    from compiler import lgraph

    board = get_device(args.model_number)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    timer = util.Timer('lgraph',path_handler)
    timer.start()
    count = 0
    for index,adp in \
        enumerate(lgraph.compile(board,
                                 program,
                                 vadp_fragments=args.vadp_fragments,
                                 asm_frags=args.asm_fragments,
                                 synth_depth=args.synth_depth,
                                 vadps=args.vadps,
                                 adps=args.adps, \
                                 routes=args.routes)):
        timer.end()
        adp.metadata.set(ADPMetadata.Keys.DSNAME, \
                         args.program)
        adp.metadata.set(ADPMetadata.Keys.FEATURE_SUBSET, \
                         args.subset)

        adp.metadata.set(ADPMetadata.Keys.LGRAPH_ID, \
                         int(index))
        print("<<< writing circuit>>>")
        filename = path_handler.lgraph_adp_file(index)
        with open(filename,'w') as fh:
            jsondata = adp.to_json()
            fh.write(json.dumps(jsondata,indent=4))

        print("<<< writing graph >>>")
        filename = path_handler.lgraph_adp_diagram_file(index)
        adprender.render(board,adp,filename)
        count += 1
        if count >= args.adps:
            break

        timer.start()

    print("<<< done >>>")
    timer.kill()
    print(timer)
    timer.save()

def exec_lcal(args):
    calib_objs = [
        llenums.CalibrateObjective.MINIMIZE_ERROR,
        llenums.CalibrateObjective.MAXIMIZE_FIT
    ]
    CAL_CMD = "python3 grendel.py cal {adp_path} --model-number {model_number} {calib_obj}"
    PROF_CMD = "python3 grendel.py prof {adp_path} --model-number {model_number} {calib_obj}"
    MKDELTAS_CMD = "python3 grendel.py mkdeltas --model-number {model_number} {adp_path} --force"
    board = get_device(None)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    timer = util.Timer('lsim',path_handler)
    for calib_obj in calib_objs:
        for dirname, subdirlist, filelist in \
            os.walk(path_handler.lgraph_adp_dir()):
            for adp_file in filelist:
                if adp_file.endswith('.adp'):
                    adp_path = dirname+"/"+adp_file
                    kwargs = {
                        'adp_path':adp_path,
                        'calib_obj':calib_obj.value,
                        'model_number':args.model_number
                    }
                    cmd = CAL_CMD.format(**kwargs)
                    print(cmd)
                    os.system(cmd)
                    cmd = PROF_CMD.format(**kwargs)
                    print(cmd)
                    os.system(cmd)
                    cmd = MKDELTAS_CMD.format(**kwargs)
                    print(cmd)
                    os.system(cmd)

def _lexec_already_ran(ph,board,adp,trial=0):
    for var,scf,chans in adp.observable_ports(board):
        filename = ph.measured_waveform_file(graph_index=adp.metadata[ADPMetadata.Keys.LGRAPH_ID], \
                                             scale_index=adp.metadata[ADPMetadata.Keys.LSCALE_ID], \
                                             model=adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD], \
                                             opt=adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                                             phys_db=adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
                                             calib_obj=adp.metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ], \
                                             variable=var, \
                                             trial=trial)

        if not os.path.exists(filename):
            return False
    return True

def exec_lexec(args):
    EXEC_CMD = "python3 grendel.py exec {adp_path} --model-number {model_number}"
    board = get_device(None)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    timer = util.Timer('lsim',path_handler)
    for dirname, subdirlist, filelist in \
        os.walk(path_handler.lscale_adp_dir()):
        for adp_file in filelist:
            if adp_file.endswith('.adp'):
                adp_path = dirname+"/"+adp_file
                print(adp_path)
                with open(adp_path,'r') as fh:
                    print("===== %s =====" % (adp_file))
                    adp = ADP.from_json(board, \
                                        json.loads(fh.read()))
                    kwargs = {
                        'adp_path': adp_path,
                        'model_number': adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB]
                    }
                    if not _lexec_already_ran(path_handler,board,adp,trial=0) or \
                       args.force:
                        cmd = EXEC_CMD.format(**kwargs)
                        os.system(cmd)

def exec_lsim(args):
    from compiler import lsim

    board = get_device(None)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    timer = util.Timer('lsim',path_handler)
    for dirname, subdirlist, filelist in \
        os.walk(path_handler.lscale_adp_dir()):
        for adp_file in filelist:
            if adp_file.endswith('.adp'):
                with open(dirname+"/"+adp_file,'r') as fh:
                    print("===== %s =====" % (adp_file))
                    adp = ADP.from_json(board, \
                                        json.loads(fh.read()))

                    plot_file = path_handler.adp_sim_plot(
                        paths.PlotType.SIMULATION, \
                        adp.metadata[ADPMetadata.Keys.DSNAME],
                        adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                        adp.metadata[ADPMetadata.Keys.LSCALE_ID],
                        adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                        adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE])



                    lsim.simulate(board,adp,plot_file)

def exec_wav(args,trials=1):
    import compiler.lwav_pass.waveform as wavelib
    import compiler.lwav_pass.analyze as analyzelib

    path_handler = paths.PathHandler(args.subset, \
                                     args.program)
    program = DSProgDB.get_prog(args.program)
    for dirname, subdirlist, filelist in \
        os.walk(path_handler.lscale_adp_dir()):
        for adp_file in filelist:
            if adp_file.endswith('.adp'):
                with open(dirname+"/"+adp_file,'r') as fh:
                    print("===== %s =====" % (adp_file))
                    obj = json.loads(fh.read())
                    metadata = ADPMetadata.from_json(obj['metadata'])
                    if not metadata.has(ADPMetadata.Keys.RUNTIME_PHYS_DB) or \
                       not metadata.has(ADPMetadata.Keys.RUNTIME_CALIB_OBJ):
                        continue

                    board = get_device(metadata.get(ADPMetadata.Keys.RUNTIME_PHYS_DB))
                    adp = ADP.from_json(board, obj)
                    for trial in range(trials):
                        for var,_,_ in adp.observable_ports(board):
                            waveform_file = path_handler.measured_waveform_file( \
                                                                                 graph_index=adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                                                                                 scale_index=adp.metadata[ADPMetadata.Keys.LSCALE_ID],
                                                                                 model=adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                                                                                 calib_obj=adp.metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ], \
                                                                                 opt=adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                                                                                 phys_db=adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
                                                                                 variable=var, \
                                                                                 trial=trial)
                            if os.path.exists(waveform_file):
                                with open(waveform_file,'r') as fh:
                                    obj = util.decompress_json(fh.read())
                                    wave = wavelib.Waveform.from_json(obj)
                                    for vis in analyzelib.analyze(adp,wave):
                                        plot_file = path_handler.waveform_plot_file( \
                                                                                             graph_index=adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                                                                                             scale_index=adp.metadata[ADPMetadata.Keys.LSCALE_ID],
                                                                                             model=adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                                                                                             calib_obj=adp.metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ], \
                                                                                             opt=adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                                                                                             phys_db=adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
                                                                                             variable=var, \
                                                                                             trial=trial, \
                                                                                     plot=vis.name)

                                        vis.plot(plot_file)
