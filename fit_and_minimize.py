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
  block,inst,cfg = targ.get_block(dev)  

  #block = dev.get_block('mult')
  #inst = devlib.Location([0,3,2,0])
  #cfg = adplib.BlockConfig.make(block,inst)
  #cfg.modes = [['+','+','-','m']]
  cfg.modes = [block.modes.get(['x','m','m'])]

  db = physdb.PhysicalDatabase('board6')
  #org = physdb.HiddenCodeOrganizer([])
  # build up dataset
  params = {}
  inputs = {}
  costs = []
  for blk in physdb.get_by_block_instance(db, dev,block,inst,cfg=cfg):
    for par,value in blk.model.params.items():
      if not par in params:
        params[par] = []
      params[par].append(value)


    for hidden_code,value in blk.hidden_codes():
      if not hidden_code in inputs:
        inputs[hidden_code] = []
      inputs[hidden_code].append(value)


    costs.append(blk.model.cost)
  #print(params)
  #print(params['params']['d'])
  
  '''
  if param == "D":
  	dataset = {'inputs':inputs, 'meas_mean':params['d']}
  	terms = ["pmos", "nmos", "gain_cal", "bias_in0", "bias_out","bias_in1", "pmos*nmos", "pmos*gain_cal", "nmos*gain_cal", "pmos*bias_out"]
  elif param == "A":
  	dataset = {'inputs':inputs, 'meas_mean':params['a']}
  	terms = ['pmos', 'nmos', 'gain_cal', 'bias_in0', 'bias_in1', 'bias_out', 'pmos*nmos', 'pmos*bias_in0', 'pmos*bias_in1', 'pmos*bias_out', 'nmos*gain_cal', 'nmos*bias_in0', 'nmos*bias_in1', 'nmos*bias_out', 'bias_in0*bias_in1', 'nmos*pmos*bias_in0', 'nmos*pmos*bias_in1', 'nmos*pmos*bias_out', 'nmos*bias_in0*bias_in1']
  elif param == "cost":
  	dataset = {'inputs':inputs, 'meas_mean':costs}
  	terms = [ "pmos","nmos","bias_in0", "bias_in1", "bias_out", "gain_cal"]
  '''

  A_dataset = {'inputs':inputs, 'meas_mean':params['a']}
  A_terms = ['pmos', 'nmos', 'gain_cal', 'bias_in0', 'bias_in1', 'bias_out', 'pmos*nmos', 'pmos*bias_in0', 'pmos*bias_in1', 'pmos*bias_out', 'nmos*gain_cal', 'nmos*bias_in0', 'nmos*bias_in1', 'nmos*bias_out', 'bias_in0*bias_in1', 'nmos*pmos*bias_in0', 'nmos*pmos*bias_in1', 'nmos*pmos*bias_out', 'nmos*bias_in0*bias_in1']
  A_variables = list(map(lambda i: "c%d" % i, range(0,len(A_terms)))) + ['offset']
  A_expr = ['offset']
  for coeff,term in zip(A_variables,A_terms):
    A_expr.append("%s*%s" % (coeff,term))
  A_expr_text = "+".join(A_expr)
  A_expr = opparse.parse_expr(A_expr_text)
  A_result = fitlib.fit_model(A_variables, A_expr, A_dataset)
  A_sub_dict = {}
  for key,value in A_result['params']:
  	A_sub_dict[key] = value
  A_baked_expr = A_expr.substitute(A_sub_dict)

  

  D_dataset = {'inputs':inputs, 'meas_mean':params['d']}
  D_terms = ["pmos", "nmos", "gain_cal", "bias_in0", "bias_out","bias_in1", "pmos*nmos", "pmos*gain_cal", "nmos*gain_cal", "pmos*bias_out"]
  D_variables = list(map(lambda i: "c%d" % i, range(0,len(D_terms)))) + ['offset']
  D_expr = ['offset']
  for coeff,term in zip(D_variables,D_terms):
    D_expr.append("%s*%s" % (coeff,term))
  D_expr_text = "+".join(D_expr)
  D_expr = opparse.parse_expr(D_expr_text)
  D_result = fitlib.fit_model(D_variables, D_expr, D_dataset)
  D_sub_dict = {}
  for key,value in D_result['params']:
  	D_sub_dict[key] = value
  D_baked_expr = D_expr.substitute(D_sub_dict)

  cost_dataset = {'inputs':inputs, 'meas_mean':costs}
  cost_terms = [ "pmos","nmos","bias_in0", "bias_in1", "bias_out", "gain_cal"]
  cost_variables = list(map(lambda i: "c%d" % i, range(0,len(cost_terms)))) + ['offset']
  cost_expr = ['offset']
  for coeff,term in zip(cost_variables,cost_terms):
    cost_expr.append("%s*%s" % (coeff,term))
  cost_expr_text = "+".join(cost_expr)
  cost_expr = opparse.parse_expr(cost_expr_text)
  cost_result = fitlib.fit_model(cost_variables, cost_expr, cost_dataset)
  cost_sub_dict = {}
  for key,value in cost_result['params']:
  	cost_sub_dict[key] = value
  cost_baked_expr = cost_expr.substitute(cost_sub_dict)
  


  A2_expr = genoplib.Mult(A_baked_expr,A_baked_expr)
  D2_expr = genoplib.Mult(D_baked_expr,D_baked_expr)
  inv_const = genoplib.Const(-1)
  inv_cost_expr = lambdoplib.Pow(cost_baked_expr,inv_const)
  prod_expr_A = genoplib.Mult(A2_expr,inv_cost_expr)
  prod_expr_B = genoplib.Mult(D2_expr,inv_cost_expr)
  sum_expr = genoplib.Add(prod_expr_A, prod_expr_B)

  expr = sum_expr
  #prod_expr = genoplib.Mult(expr,expr)
  #neg_expr = genoplib.Mult(genoplib.Const(-1.0), prod_expr)
  #expr = neg_expr
  #TODO

  #print("VARIABLES:  \n", variables, "\n\nEXPR:\n", expr, "\n\nDATASET:\n", dataset)
  #print(dataset)
  #if len(dataset['meas_mean']) == 0:
  #	raise Exception("Empty DB")


  #prediction = fitlib.predict_output(result['params'],expr,dataset)
  #error = list(map(lambda idx: dataset['meas_mean'][idx]-prediction[idx], range(0,len(prediction))))
  #sumsq_error = sum(map(lambda x:x*x,error))

  print("\n\nSUMSQ_ERROR:\n", sumsq_error,"\nERROR:\n ", error,"\n\n")
  #TODO AUTOMATE
  
  bounds = {'pmos':(0,7),\
  			'nmos':(0,7),\
  			'gain_cal':(0,63),\
  			'bias_out':(0,63),\
  			'bias_in0':(0,63),\
  			'bias_in1':(0,63),\
  }

  hidden_vars = expr.vars()
  for var in variables:
  	hidden_vars.remove(var)

  optimal_codes = fitlib.minimize_model(hidden_vars, expr, {}, bounds)

  #clean up optimal codes
  for code in optimal_codes['values']:
  	try:
  		optimal_codes['values'][code] = int(round(optimal_codes['values'][code]))
  	except:
  		print("Can't round non-numerical value")

  with open("convergence_data.txt", 'a') as file:
  	file.write("SUMSQ_ERR = %s\n PREDICTION = %s\n RESULT = %s\n" %(sumsq_error, prediction, result))




  #print("\n\nOPTIMAL CODE:\n", optimal_codes['values'])

  #print("\n\nTOTAL ERROR:\n", sumsq_error)

  #print("\n\nRESULT:\n", result)

  #return error, result['params']
  return optimal_codes['values']

#investigate_model("D")
