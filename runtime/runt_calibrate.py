from hwlib.adp import ADP,ADPMetadata

import runtime.runtime_util as runtime_util
import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as delta_model_lib

from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import time

def calibrate_adp(args):
    board = runtime_util.get_device(args.model_number)
    adp = runtime_util.get_adp(board,args.adp,widen=args.widen)
    logger = runtime_meta_util.get_calibration_time_logger(board,'calib')

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


            if delta_model_lib.is_calibrated(board, \
                                             blk, \
                                             cfg.inst.loc, \
                                             cfg, \
                                             calib_obj):
                print("-> already calibrated")
                continue

            print("== calibrate %s (%s) ==" % (cfg.inst,calib_obj.value))
            print(cfg)
            print('----')
            # calibrate block and time it
            start = time.time()
            upd_cfg = llcmd.calibrate(runtime, \
                                    board, \
                                    blk, \
                                    cfg.inst.loc,\
                                    adp, \
                                    calib_obj=calib_obj)
            end = time.time()
            runtime_sec = end-start
            logger.log(block=blk.name,loc=cfg.inst.loc, mode=mode, \
                        calib_obj=calib_obj.value, \
                        operation='cal',runtime=runtime_sec)


            for output in blk.outputs:
                delta_model = delta_model_lib.load(board,blk, \
                                                   cfg.inst.loc,\
                                                   output, \
                                                   upd_cfg, \
                                                   calib_obj=calib_obj)
                if delta_model is None:
                    delta_model = delta_model_lib \
                                  .ExpDeltaModel(blk,cfg.inst.loc, \
                                                 output, \
                                                 upd_cfg, \
                                                 calib_obj=calib_obj)

                delta_model.calib_obj = calib_obj

                # update models and time it
                start = time.time()
                delta_model_lib.update(board,delta_model)
                end = time.time()
                runtime_sec = end-start
                logger.log(block=blk.name,loc=cfg.inst.loc, mode=mode, \
                           calib_obj=calib_obj.value, \
                           operation='fit',runtime=runtime_sec)

