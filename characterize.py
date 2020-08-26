import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.llstructs as llstructs
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.physdb as physdb
import target_block
import itertools
import ops.op as oplib
from analyze import analyze_db
from lab_bench.grendel_runner import GrendelRunner
import lab_bench.grendel_util as grendel_util
from enum import Enum
import math
import numpy as np
from fit_and_minimize import investigate_model
import phys_model.profiler as proflib
import phys_model.planner as planlib

'''
dev = hcdclib.get_device()
block = dev.get_block('integ')
inst = devlib.Location([0,3,2,0])
cfg = adplib.BlockConfig.make(block,inst)
cfg.modes = [block.modes.get(['m','m','+'])]
characterize(block,inst,cfg)
'''


def replicate_config(planner, optimal_code):
    new_adp = adplib.ADP()
    new_adp.add_instance(planner.block, planner.loc)
    config = new_adp.configs.get(planner.block.name, \
                                 planner.loc)
    config.set_config(planner.config)
    for name, val in optimal_code.items():
        config[name].value = val
    return config


#block = dev.get_block('fanout')
dev = hcdclib.get_device()
block, inst, cfg = target_block.get_block(dev)
db = physdb.PhysicalDatabase('board6')
runtime = GrendelRunner()
#planner = planlib.BruteForcePlanner(block,inst,cfg,3,10)
#planner = planlib.NeighborhoodPlanner(block,inst,cfg,3,10)
#planner = planlib.SensitivityPlanner(block,inst,cfg,32,10)
#planner = planlib.CorrelationPlanner(block,inst,cfg,8,10)
#planner = planlib.ModelBasedPlanner(block,inst,cfg,8,10)
#planner = planlib.SingleTargetedPointPlanner(block,inst,cfg,10,)

planner = planlib.RandomPlanner(block, inst, cfg, 8, 10, 1000)
proflib.profile_all_hidden_states(runtime, dev, planner)
analyze_db()

'''for i in range(10):
    new_optimal_code = {}
    phys_model,optimal_code = investigate_model("A")
    for name, value in optimal_code.items():
        new_optimal_code[block.state[name]] = value

    test_planner = planlib.SinglePointPlanner(block, inst, cfg, 10)
    test_planner.new_hidden()
    proflib.profile_hidden_state(dev, runtime, test_planner, new_optimal_code)
    analyze_db()
    new_cfg = replicate_config(test_planner, optimal_code)
    
    lowest_cost = {'pmos':0,'nmos':7,'gain_cal':31, 'bias_in0':43, 'bias_in1':50, 'bias_out':8}
    lowest_pred_cost = phys_model['model_error'].compute(lowest_cost)
    with open('codes_params_cost.txt','a') as fh:
        fh.write("HARDCODED model cost:%s\n" % lowest_pred_cost)
    
    print("=======")
    for blk in physdb.get_by_block_instance(db,
                                            dev,
                                            block,
                                            inst,
                                            cfg=new_cfg,
                                            hidden=True):
       with open('codes_params_cost.txt','a') as fh:
            fh.write("hidden codes: %s\n" % list(blk.hidden_codes()))
            fh.write("observed:\n")
            fh.write("  params:%s\n" % blk.model.params)
            fh.write("  model_cost:%s\n" % blk.model.cost)
            fh.write("predicted:\n")

            pred_cost = phys_model['model_error'].compute(optimal_code)
            fh.write("   model cost:%s\n" % pred_cost)
'''
'''
first test out 15 random hidden codes
then fit models of A, D, cost to the database generated by those hidden codes
minimize one of the models, for example cost
at the hidden code corresponding to cost,

'''
