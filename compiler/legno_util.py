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

                    print("<<< writing scaled circuit %d>>>" % idx)
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
                                 adps=args.adps)):
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

def exec_lsim(args):
    from compiler import lsim

    board = get_device()
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
                                    ref,traj = analyzelib.analyze(adp,wave)
