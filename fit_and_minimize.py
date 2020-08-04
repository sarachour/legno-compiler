import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import phys_model.visualize as vizlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import ops.opparse as opparse
import ops.generic_op as genoplib
import target_block as targ
import ops.lambda_op as lambdoplib

import time
import matplotlib.pyplot as plt
import random
import time


def investigate_model(param):

    dev = hcdclib.get_device()

    targ.get_block(dev)
    block, inst, cfg = targ.get_block(dev)

    #block = dev.get_block('mult')
    #inst = devlib.Location([0,3,2,0])
    #cfg = adplib.BlockConfig.make(block,inst)
    #cfg.modes = [['+','+','-','m']]
    cfg.modes = [block.modes.get(['x', 'm', 'm'])]

    db = physdb.PhysicalDatabase('board6')
    #org = physdb.HiddenCodeOrganizer([])
    # build up dataset
    params = {}
    inputs = {}
    costs = []
    for blk in physdb.get_by_block_instance(db, dev, block, inst, cfg=cfg):
        for par, value in blk.delta_model.params.items():
            if not par in params:
                params[par] = []
            params[par].append(value)

        for hidden_code, value in blk.hidden_codes():
            if not hidden_code in inputs:
                inputs[hidden_code] = []
            inputs[hidden_code].append(value)

        costs.append(blk.delta_model.cost)
    #print(params)
    #print(params['params']['d'])
    phys_model = physdb.get_physical_models(db, dev, block, inst, cfg=cfg)

    A_expr = phys_model['a'].concrete_relation()
    A2_expr = genoplib.Mult(A_expr, A_expr)
    D_expr = phys_model['d'].concrete_relation()
    D2_expr = genoplib.Mult(D_expr, D_expr)

    cost_expr = phys_model.model_error.concrete_relation()
    inv_const = genoplib.Const(-1)
    inv_cost_expr = lambdoplib.Pow(cost_expr, inv_const)

    prod_expr_A = genoplib.Mult(A2_expr, inv_cost_expr)
    prod_expr_B = genoplib.Mult(D2_expr, inv_cost_expr)
    sum_expr = genoplib.Add(prod_expr_A, prod_expr_B)

    expr = sum_expr
    #TODO AUTOMATE
    bounds = {'pmos':(0,7),\
       'nmos':(0,7),\
       'gain_cal':(0,63),\
       'bias_out':(0,63),\
       'bias_in0':(0,63),\
       'bias_in1':(0,63),\
    }

    hidden_vars = list(set(phys_model['a'].spec.hidden_state  \
                      + phys_model['d'].spec.hidden_state  \
                      + phys_model.model_error.spec.hidden_state))
    optimal_codes = fitlib.minimize_model(hidden_vars, expr, {},
                                          bounds)

    #clean up optimal codes
    for code in optimal_codes['values']:
        try:
            optimal_codes['values'][code] = int(
                round(optimal_codes['values'][code]))
        except:
            print("Can't round non-numerical value")

    #print("\n\nOPTIMAL CODE:\n", optimal_codes['values'])

    #print("\n\nTOTAL ERROR:\n", sumsq_error)

    #print("\n\nRESULT:\n", result)

    #return error, result['params']
    return optimal_codes['values']


#investigate_model("D")
