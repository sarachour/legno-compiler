import dslang.dsprog as dsproglib

import lab_bench.devices.sigilent_osc as osclib
from lab_bench.grendel_runner import GrendelRunner

import phys_model.model_fit as fitlib
import phys_model.planner as planlib
import phys_model.profiler as proflib
import phys_model.fit_lin_dectree as fit_lindectree
import phys_model.dectree_algebra as lindectree_eval
import phys_model.lin_dectree as lindectreelib
import phys_model.visualize as vizlib

from hwlib.adp import ADP,ADPMetadata
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.physdb as physdblib
import hwlib.physdb_api as physapi
import hwlib.physdb_util as physutil
import hwlib.phys_model as physlib
import hwlib.delta_model as deltalib
import util.paths as paths
import hwlib.block as blocklib

import ops.op as oplib
import ops.generic_op as genoplib

import compiler.lscale_pass.lscale_widening as widenlib
import json
import numpy as np

def get_device(model_no,layout=False):
    assert(not model_no is None)
    import hwlib.hcdc.hcdcv2 as hcdclib
    return hcdclib.get_device(model_no,layout=layout)


def is_calibrated(board,blk,loc,cfg,label):
    for it in physapi.get_calibrated_configured_physical_block(board.physdb, \
                                                               board, \
                                                               blk, \
                                                               loc, \
                                                               cfg, \
                                                               label):
        return True

    return False
