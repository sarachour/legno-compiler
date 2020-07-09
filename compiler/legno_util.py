#from compiler import lgraph, lscale, srcgen, execprog
import os
import time
import json
import shutil
import numpy as np
import itertools
import util.util as util
import util.paths as paths
from hwlib.adp import ADP
from dslang.dsprog import DSProgDB
import json
import hwlib.adp_renderer as adprender

def exec_lgraph(args):
    from compiler import lgraph
    import hwlib.hcdc.hcdcv2 as hcdclib

    hdacv2_board = hcdclib.get_device(layout=True)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    timer = util.Timer('lgraph',path_handler)
    timer.start()
    count = 0
    for indices,adp in \
        enumerate(lgraph.compile(hdacv2_board,
                                 program,
                                 vadp_fragments=args.vadp_fragments,
                                 assembly_depth=args.assembly_depth,
                                 vadps=args.vadps,
                                 adps=args.adps)):
        timer.end()

        print("<<< writing circuit>>>")
        filename = path_handler.lgraph_adp_file(indices)
        with open(filename,'w') as fh:
            jsondata = adp.to_json()
            fh.write(json.dumps(jsondata,indent=4))

        print("<<< writing graph >>>")
        filename = path_handler.lgraph_adp_diagram_file(indices)
        #adp.write_graph(filename,write_png=True)
        adprender.render(hdacv2_board,adp,filename)
        count += 1
        if count >= args.adps:
            break

        timer.start()

    print("<<< done >>>")
    timer.kill()
    print(timer)
    timer.save()

def exec_lscale_normal(timer,prog,adp,args):
    from compiler import lscale
    timer.start()
    for idx,opt,model,scale_circ in lscale.scale(prog, \
                                                 adp,
                                                 args.scale_circuits,
                                                 model=util.DeltaModel(args.model),
                                                 max_freq_khz=args.max_freq,
                                                 ignore_models=args.ignore_model,
                                                 mdpe=args.mdpe/100.0,
                                                 mape=args.mape/100.0,
                                                 mc=args.mc/100.0,
                                                 do_log=not args.ignore_missing):
        timer.end()
        yield idx,opt,model,scale_circ
        timer.start()


def exec_lscale_search(timer,prog,adp,args,tolerance=0.01):
    from compiler import lscale
    def test_valid(mdpe,mape,vmape,mc,do_log=False):
        print("mdpe=%f mape=%f vmape=%f mc=%f" % (mdpe,mape,vmape,1.0-mc))
        assert(mc <= 1.0)
        for obj in lscale.scale(prog, \
                                adp,
                                args.scale_circuits,
                                model=util.DeltaModel(args.model),
                                max_freq_khz=args.max_freq,
                                ignore_models=args.ignore_model,
                                mdpe=mdpe,
                                mape=mape,
                                vmape=vmape,
                                mc=1.0-mc,
                                do_log=do_log,
                                test_existence=True):
            return True

        return False


    def recursive_grid_search(rng,name, \
                              defaults, \
                              n=2, \
                              failures=[]):
        vals = np.linspace(rng[0], rng[1], n)
        if abs(rng[0]-rng[1]) < tolerance:
            return None

        succs,fails = [],[]
        for value in vals:
            if value in failures:
                fails.append(value)
                continue;
            values = dict(defaults)
            values[name] = value
            is_valid = test_valid(**values)
            if is_valid:
                succs.append(value)
                break;
            else:
                fails.append(value)


        if len(succs) > 0:
            best = min(succs)
            worst = max(fails) if len(fails) > 0 else rng[0]
            if best < rng[1] or worst > rng[0]:
                best = recursive_grid_search( \
                                              [worst,best], \
                                              name=name, \
                                              defaults=defaults, \
                                              n=n,
                                              failures=failures+fails)
                best = min(succs) if best is None else best
            return best
        else:
            return None


    def joint_search(mdpe,mape,vmape,mc):
        print("mdpe=%f mape=%f vmape=%f mc=%f" % (mdpe,mape,vmape,1.0-mc))
        if test_valid(mdpe,mape,vmape,mc):
            return mdpe,mape,vmape,mc

        dig,alog,valog,cov = joint_search(mdpe+tolerance, \
                                mape+tolerance*0.5, \
                                vmape+tolerance, \
                                mc+tolerance)
        return dig,alog,valog,cov

    max_pct = 1.0
    succ = test_valid(max_pct,max_pct,max_pct,1.0, \
                      do_log=not args.ignore_missing)
    while not succ and max_pct <= 1e6:
        max_pct *= 2
        succ = test_valid(max_pct,max_pct,max_pct,1.0)

    defaults = {'mdpe':max_pct,'mape':max_pct,'vmape':max_pct,'mc':1.0}
    if max_pct >= 1e6:
        return
    analog_error= recursive_grid_search([0.01,max_pct], \
                                        defaults=defaults, \
                                        name="mape",n=3)
    var_analog_error= recursive_grid_search([0.01,max_pct], \
                                        defaults=defaults, \
                                        name="vmape",n=3)
    dig_error= recursive_grid_search([0.01,max_pct], \
                                     defaults=defaults,
                                     name="mdpe",n=3)
    coverage = recursive_grid_search([0.01,1.0], \
                                     defaults=defaults, \
                                     name="mc",
                                     n=3)
    dig_error,analog_error,var_analog_error,coverage = joint_search(dig_error, \
                                                                    analog_error, \
                                                                    var_analog_error, \
                                                                    coverage)

    assert(coverage < 0.95)
    timer.kill()
    for slack in [0.02]:
        timer.start()
        for idx,opt,model,scale_circ in lscale.scale(prog, \
                                                     adp,
                                                     args.scale_circuits,
                                                     model=util.DeltaModel(args.model),
                                                     ignore_models=args.ignore_model,
                                                     max_freq_khz=args.max_freq,
                                                     mdpe=dig_error+slack,
                                                     mape=analog_error+slack,
                                                     vmape=var_analog_error,
                                                     mc=1.0-(coverage+slack),
                                                     do_log=not args.ignore_missing):
            timer.end()
            timer.start()
            yield idx,opt,model,scale_circ



def exec_lscale(args):
    from hwlib.hcdc.hcdcv2_4 import make_board
    from hwlib.hcdc.globals import HCDCSubset

    hdacv2_board = make_board(HCDCSubset(args.subset), \
                              load_conns=False)
    path_handler = paths.PathHandler(args.subset,args.program)
    program = DSProgDB.get_prog(args.program)
    timer = util.Timer('lscale',path_handler)
    adp_dir = path_handler.lgraph_adp_dir()
    for dirname, subdirlist, filelist in os.walk(adp_dir):
        for lgraph_adp_file in filelist:
            if lgraph_adp_file.endswith('.adp'):
                fileargs = path_handler \
                           .lgraph_adp_to_args(lgraph_adp_file)
                print('<<<< %s >>>>' % lgraph_adp_file)
                lgraph_adp_filepath = "%s/%s" % (dirname,lgraph_adp_file)
                adp = AnalogDeviceProg.read(hdacv2_board, \
                                            lgraph_adp_filepath)

                gen = exec_lscale_normal(timer,program,adp,args) if not args.search \
                      else exec_lscale_search(timer,program,adp,args)

                for scale_index,opt,model,scale_adp in gen:
                    lscale_adp_file = path_handler.lscale_adp_file(fileargs['lgraph'],
                                                            scale_index,
                                                            model,
                                                            opt)
                    scale_adp.write_circuit(lscale_adp_file)
                    lscale_diag_file = path_handler.lscale_adp_diagram_file(fileargs['lgraph'],
                                                                    scale_index,
                                                                    model,
                                                                    opt)
                    scale_adp.write_graph(lscale_diag_file,write_png=True)

    timer.kill()
    timer.save()

def exec_srcgen(args):
    from compiler import srcgen
    import hwlib.hcdc.hwenvs as hwenvs
    from hwlib.hcdc.hcdcv2_4 import make_board
    from hwlib.hcdc.globals import HCDCSubset

    hdacv2_board = make_board(HCDCSubset(args.subset), \
                              load_conns=False)
    path_handler = paths.PathHandler(args.subset,args.program)
    dssim = DSProgDB.get_sim(args.program)
    hwenv = hwenvs.get_hw_env(args.hwenv  \
                              if not args.hwenv is None \
                              else dssim.hardware_env)

    adp_dir = path_handler.lscale_adp_dir()
    timer = util.Timer('srcgen', path_handler)
    for dirname, subdirlist, filelist in os.walk(adp_dir):
        for adp_file in filelist:
            if adp_file.endswith('.adp'):
                print('<<<< %s >>>>' % adp_file)
                fileargs  = \
                            path_handler.lscale_adp_to_args(adp_file)
                gren_file = path_handler.grendel_file(fileargs['lgraph'], \
                                                     fileargs['lscale'], \
                                                     fileargs['model'], \
                                                     fileargs['opt'],
                                                     dssim.name,
                                                     hwenv.name)

                if path_handler.has_file(gren_file) and not args.recompute:
                    continue

                adp_filepath = "%s/%s" % (dirname,adp_file)
                conc_circ = AnalogDeviceProg.read(hdacv2_board,adp_filepath)
                timer.start()
                gren_prog = srcgen.generate(path_handler,
                                            hdacv2_board,\
                                            conc_circ,\
                                            dssim,
                                            hwenv,
                                            filename=gren_file,
                                            ntrials=args.trials)
                timer.end()
                gren_prog.write(gren_file)

    print(timer)
    timer.save()



def exec_graph_one(hdacv2_board,path_handler,fname):
    dirname = path_handler.conc_circ_dir()
    circ_bmark,circ_indices,circ_scale_index,model,opt = \
                                                   path_handler \
                                                   .conc_circ_to_args(fname)

    conc_circ = path_handler.conc_circ_file(circ_bmark,
                                            circ_indices,
                                            circ_scale_index,
                                            model,
                                            opt)
    print('<<<< %s >>>>' % fname)
    with open("%s/%s" % (dirname,fname),'r') as fh:
        obj = json.loads(fh.read())
        conc_circ = ConcCirc.from_json(hdacv2_board, \
                                       obj)

        path_handler.extract_metadata_from_filename(conc_circ, fname)
        methods = ['snr','pctrng']
        for draw_method in methods:
            filename = path_handler.conc_graph_file(circ_bmark,
                                                    circ_indices,
                                                    circ_scale_index,
                                                    model,
                                                    opt,
                                                    tag=draw_method)
            conc_circ.write_graph(filename,\
                                  write_png=True,\
                                  color_method=draw_method)

def exec_visualize(args):
  path_handler = paths.PathHandler(args.bmark_dir,args.benchmark)
  circ_dir = path_handler.conc_circ_dir()
  scores = []
  filenames = []
  if not args.circ is None:
      exec_graph_one(hdacv2_board,path_handler,args.circ)
      return

  for dirname, subdirlist, filelist in os.walk(circ_dir):
      print(dirname)
      for fname in filelist:
          print(fname)
          if fname.endswith('.circ'):
              print(fname)
              exec_graph_one(hdacv2_board,path_handler,fname)
