import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.physdb as physdb
import hwlib.hcdc.llenums as llenums
import hwlib.hcdc.llcmd as llcmd
import hwlib.hcdc.hcdcv2 as hcdclib

def get_subarray(arr,inds):
  return list(map(lambda i: arr[i], inds))

def analyze(db,block,inst,out,cfg):
  def valid_data_point(dataset,method,idx):
    return dataset.meas_status[idx] == llenums.ProfileStatus.SUCCESS \
      and dataset.meas_method[idx] == method

  phys_block = llcmd.phys_block(db,block,inst,out,cfg)
  dataset = phys_block.dataset
  print("dataset size=%d" % dataset.size)
  indices = list(filter(lambda idx: valid_data_point(dataset, \
                                                  llenums.ProfileOpType.INPUT_OUTPUT, \
                                                  idx), range(0,dataset.size)))

  meas = get_subarray(dataset.meas_mean,indices)
  meas_stdev = get_subarray(dataset.meas_stdev,indices)
  ref = get_subarray(dataset.output, indices)



dev = hcdclib.get_device()
#block = dev.get_block('fanout')
block = dev.get_block('mult')
inst = devlib.Location([0,3,2,0])
cfg = adplib.BlockConfig.make(block,inst)
#cfg.modes = [['+','+','-','m']]
cfg.modes = [block.modes.get(['x','h','m'])]
# program hidden codes
cfg.get('pmos').value = 0
cfg.get('nmos').value = 0
cfg.get('gain_cal').value = 0
cfg.get('bias_in0').value = 0
cfg.get('bias_in1').value = 0
cfg.get('bias_out').value = 0

out = block.outputs["z"]

db = physdb.PhysicalDatabase('board6')
analyze(db,block,inst,out,cfg)

