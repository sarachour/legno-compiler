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
        self._write(self.fields,append=False)

    def _write(self,values,append=True):
        with open(self.log_file,'w' if not append else 'a') as fh:
            line = "\t".join(map(lambda v: str(v), values))
            fh.write("%s\n" % line)
            fh.flush()

    def log(self,**kwargs):
        assert(all(map(lambda f: f in kwargs, self.fields)))

        values = map(lambda f: kwargs[f], self.fields)
        self._write(values)


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
    runtime_sec = start-end
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

def fit_delta_models(board,force=False,log_file=None):
    CMD = "python3 grendel.py mkdeltas --model-number {model}"
    if force:
        CMD += " --force"
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
