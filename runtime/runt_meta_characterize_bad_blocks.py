import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib

import runtime.runtime_util as runtime_util
import runtime.runtime_meta_util as runtime_meta_util
import numpy as np

def get_offending_blocks(board,cutoff):
    final_pct_errors = []
    final_blks = []
    for blk,loc,cfg in exp_profile_dataset_lib \
        .get_configured_block_instances(board):
        characterize_block = False
        blk_pct_errors = []
        for output in blk.outputs:
            ival = output.interval[cfg.mode]
            delta_models = exp_delta_model_lib.get_fully_configured_outputs(board, \
                                                                            blk, \
                                                                            loc, \
                                                                            output, \
                                                                            cfg)
            pct_errors = []
            for delta_model in delta_models:
                pct_error = delta_model.model_error/ival.bound*100.0
                pct_errors.append(pct_error)

            if min(pct_errors) > cutoff:
                blk_pct_errors.append(min(pct_errors))
                characterize_block = True

        if characterize_block:
            final_pct_errors.append(max(blk_pct_errors))
            final_blks.append((blk,loc,cfg))

    inds = list(np.argsort(final_pct_errors))
    inds.reverse()
    for idx in inds:
        blk,loc,cfg = final_blks[idx]
        pct = final_pct_errors[idx]
        yield pct,blk,loc,cfg
 
def characterize_block(board,blk,loc,cfg):
    char_model = runtime_meta_util.get_model(board,blk,loc,cfg)


    CMDS = [ \
             "python3 grendel.py characterize {adp} --model-number {model} --grid-size 9 --num-hidden-codes 200 --adp-locs",
             "python3 grendel.py mkdeltas --model-number {model}"]


    adp_file = runtime_meta_util.generate_adp(board,blk,loc,cfg)

    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=char_model)
        print(">> %s" % cmd)
        runtime_meta_util.run_command(cmd)


def characterize_bad_blocks(args):
    board = runtime_util.get_device(args.model_number)
    for pct,blk,loc,cfg in get_offending_blocks(board,cutoff=args.cutoff):
        print("===== %s.%s (error=%f %%)" % (blk.name,loc,pct))
        print(cfg)
        if not args.dry:
           characterize_block(board,blk,loc,cfg)

