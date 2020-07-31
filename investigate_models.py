import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import phys_model.visualize as vizlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import ops.opparse as opparse
import time
import matplotlib.pyplot as plt
import random


def visualize_it(org):
  for key in org.keys():
    print("key: %s" % key)
    for codes,physblk in org.foreach(key):
      print(codes)
      vizlib.deviation(physblk,'output.png', \
                       amplitude=0.2, \
                       relative=True)
      time.sleep(1.0)

    input("continue?")

#<<<<<<< HEAD
def investigate_model(terms, param):

  dev = hcdclib.get_device()
  block = dev.get_block('mult')
  inst = devlib.Location([0,1,2,0])
  cfg = adplib.BlockConfig.make(block,inst)
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

  print(inputs)
  print(params)
  if param == "D":
    dataset = {'inputs':inputs, 'meas_mean':params['d']}
  elif param == "A":
    dataset = {'inputs':inputs, 'meas_mean':params['a']}
  elif param == "cost":
    dataset = {'inputs':inputs, 'meas_mean':costs}
  # fit model
  #
  
  #
  

  '''
  number_of_datapoints = 500
  #print(len(dataset['meas_mean']))
  #number_of_datapoints = len(dataset['meas_mean'])


  random_indexes = random.sample(range(0,len(dataset['meas_mean'])),number_of_datapoints)

  sampled_dataset = {}
  sampled_dataset['meas_mean'] = []
  sampled_dataset['inputs'] = {}
  sampled_dataset['inputs']['gain_cal'] = []
  sampled_dataset['inputs']['pmos'] = []
  sampled_dataset['inputs']['nmos'] = []
  sampled_dataset['inputs']['bias_in0'] = []
  sampled_dataset['inputs']['bias_in1'] = []
  sampled_dataset['inputs']['bias_out'] = []
  for i in random_indexes:
    sampled_dataset['meas_mean'].append(dataset['meas_mean'][i])
    sampled_dataset['inputs']['pmos'].append(dataset['inputs']['pmos'][i])
    sampled_dataset['inputs']['nmos'].append(dataset['inputs']['nmos'][i])
    sampled_dataset['inputs']['bias_in0'].append(dataset['inputs']['bias_in0'][i])
    sampled_dataset['inputs']['bias_in1'].append(dataset['inputs']['bias_in1'][i])
    sampled_dataset['inputs']['bias_out'].append(dataset['inputs']['bias_out'][i])
    sampled_dataset['inputs']['gain_cal'].append(dataset['inputs']['gain_cal'][i])

  dataset = sampled_dataset
  '''



           

  variables = list(map(lambda i: "c%d" % i, range(0,len(terms)))) \
              + ['offset']
  expr = ['offset']
  for coeff,term in zip(variables,terms):
    expr.append("%s*%s" % (coeff,term))

  expr_text = "+".join(expr)
  #print(expr_text)
  expr = opparse.parse_expr(expr_text)
  result = fitlib.fit_model(variables,expr,dataset)
  prediction = fitlib.predict_output(result['params'], \
                                     expr,dataset)

  error = list(map(lambda idx: dataset['meas_mean'][idx]-prediction[idx], \
                   range(0,len(prediction))))
  return error, result['params']
  '''
  plt.plot(dataset['meas_mean'])
  plt.plot(prediction)
  plt.savefig('predictions.png')
  plt.close()
  print("---- PARAMETERS ----")
  print(result['params'])
  print(result['param_error'])
  print("---- ERROR ---")
  
  #for i in range(len(error)):
  #  print("error ", i , " is ", error[i])

  plt.plot(error)
  #plt.show()
  plt.savefig('error.png')
  plt.close()
  #visualize_it(org)
  '''

def fit_parameters(param):

  if param == "D":
    terms = ["pmos", "nmos", "gain_cal", "bias_in0", "bias_out", "pmos*nmos", "pmos*gain_cal", "nmos*gain_cal", "pmos*bias_out"]
  elif param == "A":
    terms = ['pmos', 'nmos', 'gain_cal', 'bias_in0', 'bias_in1', 'bias_out', 'pmos*nmos', 'pmos*bias_in0', 'pmos*bias_in1', 'pmos*bias_out', 'nmos*gain_cal', 'nmos*bias_in0', 'nmos*bias_in1', 'nmos*bias_out', 'bias_in0*bias_in1', 'nmos*pmos*bias_in0', 'nmos*pmos*bias_in1', 'nmos*pmos*bias_out', 'nmos*bias_in0*bias_in1']
  elif param == "cost":
    terms = [ "pmos","nmos","bias_in0"]
  

  
  
  min_terms = terms
  num_of_iterations = len(terms)

  error, params = investigate_model(terms,param)
  sumsq_error = sum(map(lambda x:x*x,error))
  coefficients = list(params.values())
  min_index = coefficients.index(min(coefficients, key=abs))
  terms.remove(terms[min_index])


  print(params)
  print(sumsq_error)

  return

fit_parameters("A")



'''

GENERAL PROCEDURE FOR MANUALLY FINDING A MODEL
terms = [ "pmos",\
          "nmos",\
          "gain_cal",\
          "bias_in0",\
          "bias_in1",\
          "bias_out",\
          "pmos*nmos",\
          "pmos*gain_cal",\
          "pmos*bias_in0",\
          "pmos*bias_in1",\
          "pmos*bias_out",\
          "nmos*gain_cal",\
          "nmos*bias_in0",\
          "nmos*bias_in1",\
          "nmos*bias_out",\
          "gain_cal*bias_in0",\
          "gain_cal*bias_in1",\
          "gain_cal*bias_out",\
          "bias_in0*bias_in1",\
          "bias_in0*bias_out",\
          "bias_in1*bias_out",\
          "nmos*pmos*bias_in0",\
          "nmos*pmos*bias_in1",\
          "nmos*pmos*bias_out",\
          "nmos*pmos*gain_cal",\
          "nmos*bias_in0*bias_in1",\
          "nmos*bias_in0*bias_out",\
          "nmos*bias_in0*gain_cal",\
          "nmos*bias_in1*bias_out",\
          "nmos*bias_in1*gain_cal",\
          "nmos*bias_out*gain_cal",\
          "pmos*bias_in0*bias_in1",\
          "pmos*bias_in0*bias_out",\
          "pmos*bias_in0*gain_cal",\
          "pmos*bias_in1*bias_out",\
          "pmos*bias_in1*gain_cal",\
          "pmos*bias_out*gain_cal",\
          "bias_in0*bias_in1*bias_out",\
          "bias_in0*bias_in1*gain_cal",\
          "bias_in0*bias_out*gain_cal",\
          "bias_in1*bias_out*gain_cal",\
          
          ]


min_terms = terms
  num_of_iterations = len(terms)

  for i in range(1):
    error, params = investigate_model(terms,param)
    sumsq_error = sum(map(lambda x:x*x,error))
    coefficients = list(params.values())
    min_index = coefficients.index(min(coefficients, key=abs))
    terms.remove(terms[min_index])


  print(params)
  print(sumsq_error)
  '''


'''
#plt.plot(error)
#plt.show()
=======
dev = hcdclib.get_device()
block = dev.get_block('mult')
inst = devlib.Location([0,1,2,0])
cfg = adplib.BlockConfig.make(block,inst)
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

  #vizlib.deviation(blk,'output.png', \
  #                 relative=True)
  #input("continue")

  costs.append(blk.model.cost)

# fit model
dataset = {'inputs':inputs, \
           'meas_mean':costs}
# good for gain prediction
terms = ["pmos*nmos", "pmos", "nmos", "gain_cal","bias_in0"]
# ok for gain offset prediction
terms = ['bias_in0','pmos','nmos','bias_out']

variables = list(map(lambda i: "c%d" % i, range(0,len(terms)))) \
            + ['offset']
expr = ['offset']
for coeff,term in zip(variables,terms):
  expr.append("%s*%s" % (coeff,term))

expr_text = "+".join(expr)
print(expr_text)
expr = opparse.parse_expr(expr_text)
result = fitlib.fit_model(variables,expr,dataset)
prediction = fitlib.predict_output(result['params'], \
                                   expr,dataset)

plt.plot(dataset['meas_mean'])
plt.plot(prediction)
plt.savefig('predictions.png')
plt.close()
print("---- PARAMETERS ----")
print(result['params'])
print(result['param_error'])
print("---- ERROR ---")
error = list(map(lambda idx: dataset['meas_mean'][idx] \
                 -prediction[idx], \
                 range(0,len(prediction))))
plt.plot(error)
plt.savefig('error.png')
plt.close()
#visualize_it(org)
>>>>>>> calibrate-server-side
'''