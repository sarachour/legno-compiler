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

  vizlib.deviation(blk,'output.png', \
                   num_bins=32, \
                   baseline=vizlib.ReferenceType.CORRECTABLE_MODEL_PREDICTION, \
                   relative=False)

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
expr = opparse.parse_expr(expr_text)

result = fitlib.minimize_model(["pmos","nmos","gain_cal", \
                       "bias_in0","bias_out"],
                      expr,
                      {"c0":0.5,"c1":0.25, \
                       "c2":0.75,"c3":-1.2, \
                       "offset":-0.6}
)
print(result)
input("continue?")
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
