from hwlib.adp import ADP,ADPMetadata

import runtime.models.exp_delta_model as delta_model_lib
import runtime.models.exp_profile_dataset as prof_dataset_lib
import runtime.profile.planner as planlib
import runtime.profile.profiler as proflib
import runtime.runtime_util as runtime_util

from lab_bench.grendel_runner import GrendelRunner

import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd


def clear(args):
    board = runtime_util.get_device(args.model_number)
    if args.profiles:
        prof_dataset_lib \
        .remove_all(board)
