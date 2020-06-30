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
for blk in physdb.get_by_block_instance(db, dev,block,inst,cfg=cfg):
  for par,value in blk.model.params.items():
    if not par in params:
      params[par] = []
    params[par].append(value)


  for hidden_code,value in blk.hidden_codes():
    if not hidden_code in inputs:
      inputs[hidden_code] = []
    inputs[hidden_code].append(value)

# fit model
dataset = {'inputs':inputs,'meas_mean':params['d']}
variables = ['c1','c2','c3','c4','c5']
# good for gain prediction
expr_text = "c1*pmos*nmos + c2*pmos + c3*nmos + c4*gain_cal + c5"
# ok for gain offset prediction
variables = ['c1','c2','c3','c4','c5','c6']
expr_text = "c1*bias_out*gain_cal + c2*pmos + c3*nmos + c4*bias_in0 + c5*gain_cal + c6"
expr = opparse.parse_expr(expr_text)
result = fitlib.fit_model(variables,expr,dataset)
prediction = fitlib.predict_output(result['params'], \
                                   expr,dataset)

plt.plot(dataset['meas_mean'])
plt.plot(prediction)
print(result['params'])
print(result['param_error'])
plt.show()
#visualize_it(org)
