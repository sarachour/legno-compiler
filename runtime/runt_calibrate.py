from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.models.exp_delta_model as delta_model_lib

from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd

def calibrate_adp(args):
    board = runtime_util.get_device(args.model_number)
    adp = runtime_util.get_adp(board,args.adp)

    runtime = GrendelRunner()
    runtime.initialize()
    calib_obj = llenums.CalibrateObjective(args.method)
    for cfg in adp.configs:
        blk = board.get_block(cfg.inst.block)

        cfg_modes = cfg.modes
        for mode in cfg_modes:
            cfg.modes = [mode]
            if not blk.requires_calibration():
                continue

            print("%s" % (cfg.inst))
            print(cfg)
            print('----')

            if delta_model_lib.is_calibrated(board, \
                                             blk,cfg.inst.loc, \
                                             cfg,calib_obj):
                print("-> already calibrated")
                continue

            '''
            upd_cfg = llcmd.calibrate(runtime, \
                                      board, \
                                      blk, \
                                      cfg.inst.loc,\
                                      adp, \
                                      calib_obj=calib_obj)
            '''
            upd_cfg = cfg
            for output in blk.outputs:
                delta_model = delta_model_lib.load(board,blk, \
                                                   cfg.inst.loc,\
                                                   output,upd_cfg)
                if delta_model is None:
                    delta_model = delta_model_lib \
                                  .ExpDeltaModel(blk,cfg.inst.loc, \
                                                 output,upd_cfg)

                delta_model.calib_obj = calib_obj
                delta_model_lib.update(board,delta_model)
