#from compiler import lgraph, lscale, srcgen, execprog
import os
import time
import json
import shutil
import signal
import numpy as np
import itertools

import util.util as util
import util.paths as paths
from dslang.dsprog import DSProgDB
from hwlib.adp import ADP,ADPMetadata
import hwlib.adp_renderer as adprender
import hwlib.hcdc.llenums as llenums

import runtime.runtime_meta_util as runt_meta_util


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


                if args.no_scale and not scale_method is scalelib.ScaleMethod.IDEAL:
                    raise Exception("cannot disable scaling transform if you're using the delta model database")

                timer.start()
                for idx,scale_adp in enumerate(lscale.scale(board, \
                                                            program, \
                                                            adp, \
                                                            objective=obj, \
                                                            scale_method=scale_method, \
                                                            calib_obj=calib_obj, \
                                                            no_scale=args.no_scale, \
                                                            one_mode=args.one_mode)):
                    timer.end()

                    print("<<< writing scaled circuit %d/%d>>>" % (idx,args.scale_adps))
                    scale_adp.metadata.set(ADPMetadata.Keys.LSCALE_ID,idx)

                    calib_obj = llenums.CalibrateObjective(scale_adp \
                                                       .metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ])
                    filename = path_handler.lscale_adp_file(
                        scale_adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                        scale_adp.metadata[ADPMetadata.Keys.LSCALE_ID],
                        scale_adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                        scale_adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE],
                        calib_obj,
                        scale_adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
                        no_scale=scale_adp.metadata[ADPMetadata.Keys.LSCALE_NO_SCALE], \
                        one_mode=scale_adp.metadata[ADPMetadata.Keys.LSCALE_ONE_MODE] \
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
                        calib_obj,
                        scale_adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
                        no_scale=scale_adp.metadata[ADPMetadata.Keys.LSCALE_NO_SCALE], \
                        one_mode=scale_adp.metadata[ADPMetadata.Keys.LSCALE_ONE_MODE] \
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
    if args.model_number is None:
       raise Exception("model number must be provided to calibration procedure")

    board = get_device(args.model_number)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    for dirname, subdirlist, filelist in \
        os.walk(path_handler.lgraph_adp_dir()):
        for adp_file in filelist:
            if adp_file.endswith('.adp'):
                adp_path = dirname+"/"+adp_file
                if args.maximize_fit:
                    runt_meta_util.legacy_calibration(board, adp_path, \
                                                      llenums.CalibrateObjective.MAXIMIZE_FIT, \
                                                      widen=True,
                                                      logfile=None)
                if args.minimize_error:
                    runt_meta_util.legacy_calibration(board, adp_path, \
                                                      llenums.CalibrateObjective.MINIMIZE_ERROR, \
                                                      widen=True,
                                                      logfile=None)



def _lexec_already_ran(ph,board,adp,trial=0,scope=False):
    calib_obj = llenums.CalibrateObjective(adp \
                            .metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ])

    for var,scf,chans in adp.observable_ports(board):
        filename = ph.measured_waveform_file(graph_index=adp.metadata[ADPMetadata.Keys.LGRAPH_ID], \
                                             scale_index=adp.metadata[ADPMetadata.Keys.LSCALE_ID], \
                                             model=adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD], \
                                             opt=adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                                             no_scale=adp.metadata[ADPMetadata.Keys.LSCALE_NO_SCALE], \
                                             one_mode=adp.metadata[ADPMetadata.Keys.LSCALE_ONE_MODE], \
                                             phys_db=adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
                                             calib_obj=calib_obj, \
                                             variable=var, \
                                             trial=trial, \
                                             oscilloscope=scope)

        if not os.path.exists(filename):
            return False
    return True

def exec_lexec(args):
    EXEC_CMD = "python3 grendel.py exec {adp_path} --model-number {model_number}"
    if args.scope:
        EXEC_CMD += " --osc"

    board = get_device(None)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    timer = util.Timer('lexec',path_handler)
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
                    if not _lexec_already_ran(path_handler,board,adp,trial=0, \
                                              scope=args.scope) or \
                       args.force:
                        timer.start()
                        cmd = EXEC_CMD.format(**kwargs)
                        code = os.system(cmd)
                        timer.end()
                        #input("continue")
                        if code == signal.SIGINT or code != 0:
                            raise Exception("User terminated process")

        print(timer)
        timer.save()

def exec_lsim(args):
    from compiler import lsim

    board = get_device(None)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    plot_file = path_handler.adp_sim_plot(
        paths.PlotType.SIMULATION, \
        program.name, \
        'REF',
        'na',
        'na',
        'na', \
        per_variable=args.separate_figures)
    lsim.simulate_reference(board,program,plot_file, \
                            separate_figures=args.separate_figures)


def exec_lemul(args):
    from compiler import lsim

    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    timer = util.Timer('emul',path_handler)

    if args.unscaled:
        direc = path_handler.lgraph_adp_dir()
    else:
        direc = path_handler.lscale_adp_dir()

    board = get_device(None)
    for dirname, subdirlist, filelist in \
        os.walk(direc):
        for adp_file in filelist:
            if adp_file.endswith('.adp'):
                with open(dirname+"/"+adp_file,'r') as fh:
                    print("===== %s =====" % (adp_file))
                    adp = ADP.from_json(board, \
                                        json.loads(fh.read()))

                    if args.unscaled:
                        for cfg in adp.configs:
                            cfg.modes = [cfg.modes[0]]
                        plot_file = path_handler.adp_sim_plot(
                            paths.PlotType.SIMULATION, \
                            adp.metadata[ADPMetadata.Keys.DSNAME],
                            adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                            'na',
                            'na',
                            'na', \
                            per_variable=args.separate_figures)

                    else:
                        plot_file = path_handler.adp_sim_plot(
                            paths.PlotType.SIMULATION, \
                            adp.metadata[ADPMetadata.Keys.DSNAME],
                            adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                            adp.metadata[ADPMetadata.Keys.LSCALE_ID],
                            adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                            adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                            per_variable=args.separate_figures)

                    print(plot_file)


                    board = get_device(adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB])
                    lsim.simulate_adp(board,adp,plot_file, \
                                      enable_quantization=not args.no_quantize, \
                                      enable_intervals=not args.no_operating_range, \
                                      enable_physical_model= not args.no_physdb, \
                                      enable_model_error =not args.no_model_error, \
                                      separate_figures=args.separate_figures)

def print_runtime_stats(path_handler):
    lgraph = util.Timer.load('lgraph',path_handler)
    lscale = util.Timer.load('lscale',path_handler)
    lexec = util.Timer.load('lexec',path_handler)
    print("----- runtime statistics -----")
    print(lgraph)
    print(lscale)
    print(lexec)

def exec_stats(args,trials=1):
    import compiler.lwav_pass.waveform as wavelib
    import compiler.lwav_pass.vis_lscale_stats as  lscale_vizlib
    import compiler.lwav_pass.vis_lgraph_stats as  lgraph_vizlib
    import compiler.lwav_pass.vis_general_stats as  general_vizlib

    error_key = lambda adp : (
        adp.metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ], \
        adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD], \
        adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
        adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
        adp.metadata[ADPMetadata.Keys.LSCALE_NO_SCALE], \
        adp.metadata[ADPMetadata.Keys.LSCALE_ONE_MODE])

    pretty_print_key = lambda key : "%s %s-%s-%s %s %s" % (key[3],key[0],key[1],key[2], \
                                                        ":noscale" if key[4] else "", \
                                                        ":onemode" if key[5] else "")

    adps_by_category = {}
    def update_adp_info(adp_name,adp):
        key = error_key(adp)
        if not key in adps_by_category:
            adps_by_category[key] = []

        adps_by_category[key].append(adp)

    path_handler = paths.PathHandler(args.subset, \
                                     args.program)
    program = DSProgDB.get_prog(args.program)
    scope_options = [True,False]

    if args.runtimes_only:
        print("------------ runtime ----------------")
        print_runtime_stats(path_handler)
        return

    for dirname, subdirlist, filelist in \
        os.walk(path_handler.lscale_adp_dir()):
        for adp_file in filelist:
            if adp_file.endswith('.adp'):
                with open(dirname+"/"+adp_file,'r') as fh:
                    print("===== %s =====" % (adp_file))
                    adp_obj = json.loads(fh.read())
                    metadata = ADPMetadata.from_json(adp_obj['metadata'])
                    if not metadata.has(ADPMetadata.Keys.RUNTIME_PHYS_DB) or \
                       not metadata.has(ADPMetadata.Keys.RUNTIME_CALIB_OBJ):
                        continue

                    board = get_device(metadata.get(ADPMetadata.Keys.RUNTIME_PHYS_DB))
                    adp = ADP.from_json(board, adp_obj)
                    update_adp_info(adp_file,adp)


    print("=========== RUNTIME INFO ======")
    print_runtime_stats(path_handler)

    categories = list(adps_by_category.keys())
    sorted_inds = np.argsort(list(map(lambda key: pretty_print_key(key),  \
                                      categories)))

    overall_best_adp = None
    overall_best_execution = None
    for idx  in sorted_inds:
        adps = adps_by_category[categories[idx]]
        rmses = list(map(lambda adp: adp.metadata[ADPMetadata.Keys.LWAV_NRMSE], adps))
        b2w_inds = np.argsort(rmses)
        category_name = pretty_print_key(categories[idx])
        best_adp = adps[b2w_inds[0]]
        if overall_best_adp is None \
           or rmses[b2w_inds[0]] < overall_best_adp.metadata[ADPMetadata.Keys.LWAV_NRMSE]:
            overall_best_adp = best_adp
            overall_best_execution = categories[idx]

        for vizlib in [general_vizlib, lgraph_vizlib,lscale_vizlib]:
            vises = vizlib.print_summary(board,adp)
            vises += vizlib.print_aggregate_summaries(board,adps)
            for vis in vises:
                calib_obj = llenums.CalibrateObjective(best_adp.metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ])
                plot_file = path_handler.summary_plot_file( \
                                                model=best_adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                                                calib_obj=calib_obj, \
                                                opt=best_adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                                                phys_db=best_adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
                                                variable="", \
                                                plot=vis.name, \
                                                no_scale=best_adp.metadata[ADPMetadata.Keys.LSCALE_NO_SCALE], \
                                                one_mode=best_adp.metadata[ADPMetadata.Keys.LSCALE_ONE_MODE])
                vis.plot(plot_file)



    print("BEST EXECUTION: %s" % pretty_print_key(overall_best_execution))






def exec_wav(args,trials=1):
    import compiler.lwav_pass.waveform as wavelib
    import compiler.lwav_pass.vis_waveform as  vizlib

    path_handler = paths.PathHandler(args.subset, \
                                     args.program)
    program = DSProgDB.get_prog(args.program)

    # bin summary plots
    summary = {}
    summary_key = lambda adp : (
        adp.metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ], \
        adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD], \
        adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
        adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
        adp.metadata[ADPMetadata.Keys.LSCALE_NO_SCALE], \
        adp.metadata[ADPMetadata.Keys.LSCALE_ONE_MODE])

    def update_summary(adp,var,wave,has_scope=False):
        key = (summary_key(adp),var,has_scope)
        if not key in summary:
            summary[key] = []

        summary[key].append((adp,wave))

    assert(not args.scope_only or not args.adc_only)
    if args.scope_only:
        scope_options = [True]
    elif args.adc_only:
        scope_options = [False]
    else:
        scope_options = [True,False]

    for dirname, subdirlist, filelist in \
        os.walk(path_handler.lscale_adp_dir()):
        for adp_file in filelist:
            if adp_file.endswith('.adp'):
                adp_path = dirname+"/"+adp_file
                with open(adp_path,'r') as fh:
                    print("===== %s =====" % (adp_file))
                    adp_obj = json.loads(fh.read())
                    metadata = ADPMetadata.from_json(adp_obj['metadata'])
                    if not metadata.has(ADPMetadata.Keys.RUNTIME_PHYS_DB) or \
                       not metadata.has(ADPMetadata.Keys.RUNTIME_CALIB_OBJ):
                        continue

                    board = get_device(metadata.get(ADPMetadata.Keys.RUNTIME_PHYS_DB))
                    master_adp = ADP.from_json(board, adp_obj)
                    calib_obj = llenums.CalibrateObjective(master_adp.metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ])

                    # Analyze waveforms
                    nrmses = []
                    for trial in range(trials):
                        for var,_,_ in master_adp.observable_ports(board):
                            for has_scope in scope_options:
                                print("------- %s [has_scope=%s] ----" % (adp_file,has_scope))
                                waveform_file = path_handler.measured_waveform_file( \
                                                                                     graph_index=master_adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                                                                                     scale_index=master_adp.metadata[ADPMetadata.Keys.LSCALE_ID],
                                                                                     model=master_adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                                                                                     calib_obj=calib_obj, \
                                                                                     opt=master_adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                                                                                     phys_db=master_adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB] , \
                                                                                     no_scale=master_adp.metadata[ADPMetadata.Keys.LSCALE_NO_SCALE], \
                                                                                     one_mode=master_adp.metadata[ADPMetadata.Keys.LSCALE_ONE_MODE], \
                                                                                     variable=var, \
                                                                                     trial=trial, \
                                                                                     oscilloscope=has_scope)

                                if os.path.exists(waveform_file):
                                    with open(waveform_file,'r') as fh:
                                        obj = util.decompress_json(fh.read())
                                        wave = wavelib.Waveform.from_json(obj)
                                        adp = ADP.from_json(board, adp_obj)
                                        update_summary(adp,var,wave,has_scope=has_scope)
                                        for vis in vizlib.plot_waveform(board,adp,wave, \
                                                                            emulate=args.emulate, \
                                                                            measured=args.measured):
                                            plot_file = path_handler.waveform_plot_file( \
                                                                                         graph_index=adp.metadata[ADPMetadata.Keys.LGRAPH_ID],
                                                                                         scale_index=adp.metadata[ADPMetadata.Keys.LSCALE_ID],
                                                                                         model=adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                                                                                         calib_obj=calib_obj, \
                                                                                         opt=adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                                                                                         phys_db=adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB],  \
                                                                                         no_scale=adp.metadata[ADPMetadata.Keys.LSCALE_NO_SCALE], \
                                                                                         one_mode=adp.metadata[ADPMetadata.Keys.LSCALE_ONE_MODE], \
                                                                                         variable=var, \
                                                                                         trial=trial, \
                                                                                         plot=vis.name, \
                                                                                         oscilloscope=has_scope)

                                            vis.plot(plot_file)

                                        nrmse = adp.metadata.get(ADPMetadata.Keys.LWAV_NRMSE)
                                        nrmses.append(nrmse)

                        master_adp.metadata.set(ADPMetadata.Keys.LWAV_NRMSE, min(nrmses))
                        with open(adp_path,'w') as fh:
                            jsondata = master_adp.to_json()
                            fh.write(json.dumps(jsondata,indent=4))

        if args.summary_plots:
            for (fields,var,has_scope),data in summary.items():
                adps = list(map(lambda d: d[0], data))
                waveforms = list(map(lambda d: d[1], data))
                board = get_device(adps[0].metadata.get(ADPMetadata.Keys.RUNTIME_PHYS_DB))
                for vis in vizlib.plot_waveform_summaries(board,adps,waveforms):
                    adp = data[0][0]
                    calib_obj = llenums.CalibrateObjective(adp.metadata[ADPMetadata.Keys.RUNTIME_CALIB_OBJ])
                    plot_file = path_handler.summary_plot_file( \
                                                                model=adp.metadata[ADPMetadata.Keys.LSCALE_SCALE_METHOD],
                                                                calib_obj=calib_obj, \
                                                                opt=adp.metadata[ADPMetadata.Keys.LSCALE_OBJECTIVE], \
                                                                phys_db=adp.metadata[ADPMetadata.Keys.RUNTIME_PHYS_DB], \
                                                                variable=var, \
                                                                plot=vis.name, \
                                                                oscilloscope=has_scope, \
                                                                no_scale=adp.metadata[ADPMetadata.Keys.LSCALE_NO_SCALE], \
                                                                one_mode=adp.metadata[ADPMetadata.Keys.LSCALE_ONE_MODE])
                    vis.plot(plot_file)

