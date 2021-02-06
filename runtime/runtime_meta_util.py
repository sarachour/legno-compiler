import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.dectree.dectree as dectreelib

import ops.generic_op as genoplib
import util.paths as pathlib
import hwlib.adp as adplib
import hwlib.block as blocklib
import os
import json
import random
import os
import time

class Logger:

    def __init__(self,logfile,fields):
        self.log_file = logfile
        self.fields = fields
        # write the file header if one doesn't exist...
        self._write_header(self.fields)

    def _write_header(self,header):
        def report_error(file_header,msg):
            print("file header: %s" % str(file_header))
            print("log header: %s" % str(header))
            raise Exception(msg)

        if os.path.exists(self.log_file):
            with open(self.log_file,'r') as fh:
                file_fields = fh.readline().strip().split('\t')
                if len(file_fields) != len(header):
                    report_error(file_fields, \
                                 "header has different number of fields: %d != %d" \
                                 % (len(file_fields), len(header)))

                for f1, f2 in zip(header,file_fields):
                    if f1 != f2:
                        report_error(file_fields, \
                                 "header has field mismatch: %s != %s" \
                                 % (f1,f2))

        else:
            self._write(header,append=False)

    def _write(self,values,append=True):
        with open(self.log_file,'w' if not append else 'a') as fh:
            line = "\t".join(map(lambda v: str(v), values))
            fh.write("%s\n" % line)
            fh.flush()

    def log(self,**kwargs):
        assert(all(map(lambda f: f in kwargs, self.fields)))

        values = map(lambda f: kwargs[f], self.fields)
        self._write(values)


def get_tolerance(block,mode):
  if block.name == 'fanout':
    if 'h' in str(mode):
      return 0.004
    elif 'm' in str(mode):
      return 0.0004
    else:
      raise Exception("unknown cutoff %s <%s>" % (block.name,mode))
  
  elif block.name == 'dac':
    if 'h' in str(mode):
      return 0.01
    elif 'm' in str(mode):
      return 0.01
    else:
      raise Exception("unknown cutoff %s <%s>" % (block.name,mode))

  elif block.name == 'adc':
    if 'h' in str(mode):
      return 0.0
    elif 'm' in str(mode):
      return 0.0
    else:
      raise Exception("unknown cutoff %s <%s>" % (block.name,mode))


  elif block.name == 'integ':
    if 'h,h' in str(mode):
      return 0.009

    elif 'h,m' in str(mode):
      return 0.008

    elif 'm,m' in str(mode):
      return 0.008

    else:
      raise Exception("unknown cutoff %s <%s>" % (block.name,mode))

  elif block.name == 'mult':
    if 'x,h,h' in str(mode):
      # majority of error is from non-unity gain
      return 0.008

    elif 'x,h,m' in str(mode):
      return 0.005

    elif 'x,m,h' in str(mode):
      # majority of error is from non-unity gain
      return 0.008

    elif 'x,m,m' in str(mode):
      return 0.008

    elif 'h,m,m' in str(mode):
      return 0.004

    else:
      return 0.0

  else:
    raise Exception("unknown block cutoff: %s" % (block.name))


def random_hidden_codes(block):
    hidden_codes = {}
    for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), \
                        block.state):
          hidden_codes[state.name] = random.choice(state.values)

    return hidden_codes

def get_base_name(board,blk,loc,cfg):
    addr = "_".join(map(lambda i: str(i), loc.address))
    mode = "_".join(map(lambda m: str(m), cfg.mode))
    return "%s-%s-%s-%s" % (board.model_number,blk.name,addr,mode)

def get_model(board,blk,loc,cfg):
    return '%s' % (get_base_name(board,blk,loc,cfg))

def get_adp(board,blk,loc,cfg):
    return '%s.adp' % (get_base_name(board,blk,loc,cfg))

def run_command(cmd):
    start = time.time()
    code = os.system(cmd)
    if code != 0:
        raise Exception("command failed. <code=%s>" % code)
    end = time.time()
    runtime_sec = end-start
    return runtime_sec

def remove_file(name):
    if os.path.exists(name):
        os.remove(name)

def generate_adp(board,blk,loc,cfg):
    adp_file = get_adp(board,blk,loc,cfg)

    new_adp = adplib.ADP()
    new_adp.add_instance(blk,loc)
    blkcfg = new_adp.configs.get(blk.name,loc)
    blkcfg.set_config(cfg)

    with open(adp_file,'w') as fh:
        text = json.dumps(new_adp.to_json())
        fh.write(text)

    return adp_file

def database_is_empty(board):
    for model in exp_delta_model_lib.get_all(board):
        return False
    return True

def models_are_homogenous(models,enable_outputs=False):
    modes = []
    locs = []
    outputs = []
    blocks = []
    for model in models:
        modes.append(model.config.mode)
        locs.append(model.loc)
        outputs.append(model.output.name)
        blocks.append(model.block.name)

    # test that the data is homogenous
    if len(set(locs)) != 1:
        print("[not homogenous] # locs=%d" % (len(set(locs))))
        return False

    # test that the data is homogenous
    if len(set(modes)) != 1:
        print("[not homogenous] # modes=%d" % (len(set(modes))))
        return False

    if len(set(outputs)) != 1 and not enable_outputs:
        print("[not homogenous] # outputs=%d" % (len(set(outputs))))
        return False

    if len(set(blocks)) != 1:
        print("[not homogenous] # blocks=%d" % (len(set(blocks))))
        return False

    return True


def database_is_homogenous(board,enable_outputs=False):
    models = list(exp_delta_model_lib.get_all(board))
    return models_are_homogenous(models, \
                                 enable_outputs=enable_outputs)


def get_calibration_objective_scores(all_models):
    #assert(models_are_homogenous(all_models,enable_outputs=False))
    block,loc,_,config = models_get_block_info(all_models,use_output=False)
    phys_models = {}
    models = {}

    for model in all_models:
        calib_obj = model.output.deltas[model.config.mode].objective
        if not model.hidden_cfg in phys_models:
            phys_models[model.hidden_cfg] = exp_phys_model_lib.ExpPhysModel(block, \
                                                                          config)
            models[model.hidden_cfg] = []

        phys_model = phys_models[model.hidden_cfg]
        models[model.hidden_cfg].append(model)

        for varname,val in model.variables().items():
            node = dectreelib.RegressionLeafNode(genoplib.Const(val))
            phys_model.set_variable(model.output, varname, node)


    for hidden_cfg,model in phys_models.items():
        variables = dict(map(lambda tup: (tup[0],tup[1].expr.compute()), \
                             model.variables().items()))
        print(variables)
        calib_expr = model.calib_obj()
        if not all(map(lambda v: v in variables, calib_expr.vars())):
            continue

        yield models[hidden_cfg],calib_expr.compute(variables)


def homogenous_database_get_calibration_objective_scores(board):
    all_models = list(exp_delta_model_lib.get_all(board))
    for models,score in get_calibration_objective_scores(all_models):
        yield models,score

def models_get_block_info(models,use_output=True):
    assert(models_are_homogenous(models,enable_outputs=not use_output))
    for model in models:
        return model.block,model.loc,model.output,model.config


def homogenous_database_get_block_info(board,use_output=True):
    models = list(exp_delta_model_lib.get_all(board))
    return models_get_block_info(models,use_output)


def profile_block(board,block,loc,config,calib_obj,log_file=None):
    CMD = "python3 grendel.py prof --grid-size 15 --model-number {model} {adp} {calib_obj}"
    if not log_file is None:
        CMD += " > %s" % log_file

    filename = generate_adp(board,block,loc,config)

    cmd = CMD.format(model=board.model_number, \
                     adp=filename, \
                     calib_obj=calib_obj.value)
    run_command(cmd)


def profile(board,char_board,calib_obj,log_file=None):
    CMD = "python3 grendel.py prof --grid-size 15 --model-number {model} {adp} {calib_obj}"
    if not log_file is None:
        CMD += " > %s" % log_file

    block,loc,config = homogenous_database_get_block_info(char_board,use_output=False)

    filename = generate_adp(char_board,block,loc,config)

    cmd = CMD.format(model=board.model_number, \
                     adp=filename, \
                     calib_obj=calib_obj.value)
    run_command(cmd)

def fit_delta_models(board,force=False,orphans=True,log_file=None):
    CMD = "python3 grendel.py mkdeltas --model-number {model}"
    if force:
        CMD += " --force"
    if not orphans:
        CMD += " --no-orphans"
    if not log_file is None:
        CMD += " > %s" % log_file

    cmd = CMD.format(model=board.model_number)
    run_command(cmd)


def get_block_databases(model_number):
    for root,dirs,files in os.walk(pathlib.DeviceStatePathHandler.DEVICE_STATE_DIR):
        for filename in files:
            if not filename.endswith('.db'):
                continue
            if filename.startswith('hcdcv2-%s-' % model_number):
                dbname = filename.split('hcdcv2-')[1].split('.db')[0]
                yield dbname

def get_calibration_time_logger(board,logname):
  fields = ['block','loc','mode','calib_obj','operation','runtime']
  logger = Logger('%s_%s.log' % (logname,board.model_number), fields)
  return logger

def legacy_calibration(board,adp_path,calib_obj,widen=False,logfile=None,**kwargs):
  CAL_CMD = 'cal',"python3 grendel.py cal {adp_path} --model-number {model_number} {calib_obj} {widen}"
  PROF_CMD = 'prof',"python3 grendel.py prof {adp_path} --model-number {model_number} {calib_obj} {widen}"
  MKDELTAS_CMD = 'deltas',"python3 grendel.py mkdeltas --model-number {model_number} --force --no-orphans"

  widen_flag = " --widen" if widen else ""
  cmds = []
  for label,CMD in [CAL_CMD, PROF_CMD, MKDELTAS_CMD]:
    cmd = CMD.format(adp_path=adp_path, \
                     model_number=board.model_number, \
                     calib_obj=calib_obj.value, \
                     widen=widen_flag)
    cmds.append((label,cmd))

  logger = None if logfile is None else \
      get_calibration_time_logger(board,logfile)
  for name,cmd in cmds:
        print(cmd)
        runtime = run_command(cmd)
        if not logger is None:
            block_name = kwargs['block'].name
            loc = str(kwargs['loc'])
            mode = str(kwargs['mode'])
            logger.log(block=block_name, loc=loc, mode=mode, \
                       calib_obj=calib_obj.value,  \
                       operation=name, \
                       runtime=runtime)




def get_model_calibration_config(**kwargs):
    if 'block' in kwargs and 'mode' in kwargs:
        block = kwargs['block']
        mode = kwargs['mode']
        cutoff = get_tolerance(block,mode)
    else:
        cutoff = 0.0

    return {
        'bootstrap_samples': 15,
        'candidate_samples':3,
        'num_iters': 18,
        'grid_size': 7,
        'cutoff':cutoff
    }


def model_based_calibration(board,adp_path,widen=False,logfile=None,**kwargs):
  CAL_CMD = "python3 meta_grendel.py model_cal {model_number} --adp {adp_path}"
  CAL_CMD += " --bootstrap-samples {bootstrap_samples}"
  CAL_CMD += " --candidate-samples {candidate_samples}"
  CAL_CMD += " --num-iters {num_iters}"
  CAL_CMD += " --grid-size {grid_size}"
  CAL_CMD += " --default-cutoff > log.txt"
  if widen:
      CAL_CMD += " --widen"

  cmds = []
  cfg = get_model_calibration_config(**kwargs)
  cfg['model_number'] = board.model_number
  cfg['adp_path'] = adp_path
  cmds.append(('model_cal', CAL_CMD.format(**cfg)))

  logger = None if logfile is None else \
      get_calibration_time_logger(board,logfile)


  for name,cmd in cmds:
        print(cmd)
        runtime = run_command(cmd)
        if not logger is None:
            block_name = kwargs['block'].name
            loc = str(kwargs['loc'])
            mode = str(kwargs['mode'])
            logger.log(block=block_name, loc=loc, mode=mode, \
                       calib_obj='model',  \
                       operation=name, \
                       runtime=runtime)



  return cmds

def model_based_calibration_finalize(board,logfile=None):
    BRCAL_CMD = "python3 meta_grendel.py bruteforce_cal {model_number}"
    cmds = []
    cmds.append(('brute_cal',BRCAL_CMD.format(model_number=board.model_number)))


    logger = None if logfile is None else \
        get_calibration_time_logger(board,logfile)


    for name,cmd in cmds:
        runtime = run_command(cmd)
        if not logger is None:
           logger.log(block='', loc='', mode='', \
                      calib_obj='model',operation=name, \
                      runtime=runtime)




