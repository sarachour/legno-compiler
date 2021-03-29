import runtime.runtime_util as runtime_util
import runtime.runtime_meta_util as runtime_meta_util
import runtime.models.exp_delta_model as exp_delta_model_lib
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.models.exp_profile_dataset as exp_profile_dataset_lib

import runtime.activecal_pass.dominance as domlib
import runtime.activecal_pass.predictor as predlib
import runtime.activecal_pass.sampler as samplelib
import runtime.activecal_pass.hidden_code_pool as poollib

import hwlib.hcdc.llenums as llenums
import math
import random
import time


class ModelCalibrateLogger(runtime_meta_util.Logger):

    def __init__(self,filename):
        self.fields = ['block','loc','mode','operation','iteration','runtime']
        runtime_meta_util.Logger.__init__(self,filename,self.fields)

    def log(self,operation,runtime):
        values = {'block':self.block.name, \
                  'loc':str(self.loc),\
                  'mode':str(self.mode), \
                  'iteration': self.iteration}

        values['operation'] = operation
        values['runtime'] = runtime
        runtime_meta_util.Logger.log(self,**values)


    def set_configured_block(self,block,loc,mode):
        self.block = block
        self.loc = loc
        self.mode = mode
        self.iteration = 0


    def set_iteration(self,idx):
        self.iteration = idx

def insert_into_dict(d,ks,v):
    for k in ks[:-1]:
        if not k in d:
            d[k] = {}
        d = d[k]
    if not ks[-1] in d:
        d[ks[-1]] = []
    d[ks[-1]].append(v)


def load_code_pool_from_database(char_board,predictor,objectives):
    hidden_codes = list(map(lambda st: st.name, \
                            runtime_util.get_hidden_codes(predictor.block)))
    code_pool= poollib.HiddenCodePool(hidden_codes,predictor,objectives)
    # setting ranges of values in code pool
    for hc in hidden_codes:
        vals  = predictor.block.state[hc].values
        code_pool.set_range(hc,vals)

    by_output = {}
    print("===== Database Models ====")
    for mdl in exp_delta_model_lib.get_all(char_board):
        print(mdl)
        insert_into_dict(by_output, [mdl.hidden_cfg], mdl)

    print("===== Initial Code Pool ====")
    for _,mdls in by_output.items():
        if any(map(lambda mdl: not mdl.complete, mdls)):
           continue

        codes = dict(mdls[0].hidden_codes())
        pred_deltavars,pred_errors  = code_pool.predictor.predict(codes)
        pred_obj = code_pool.objectives.compute(pred_deltavars,pred_errors)

        actual_deltavars = {}
        actual_errors = {}
        for mdl in mdls:
            actual_deltavars[mdl.output.name] = mdl.variables()
            actual_errors[mdl.output.name] = mdl.model_error.errors()

        actual_obj = code_pool.objectives.compute(actual_deltavars,actual_errors)
        for index in range(min(len(actual_obj),len(pred_obj))):
            act_name,act_val,_,_ = actual_obj.get_by_index(index)
            pred_name,pred_val,_,_ = pred_obj.get_by_index(index)
            assert(act_name == pred_name)
            print("  obj=%s pred=%f meas=%f" % (act_name, \
                                                pred_val, \
                                                act_val))

        if not code_pool.has_code(codes):
           code_pool .add_labeled_code(codes,actual_deltavars,actual_errors)

    print("==== pool (best to worst) ====")
    print(predictor.config)
    print("")
    for fxn,score in code_pool.meas_view.order_by_dominance():
        print("%s  result=%s" % (fxn,score))

    return code_pool


def update_model(logger,char_board,blk,loc,cfg,npts_spat_error):
    #"python3 grendel.py mkphys --model-number {model} --max-depth 0 --num-leaves 1 --shrink"
    assert(isinstance(npts_spat_error,int))
    CMDS = [ \
             "python3 grendel.py mkdeltas {model} --force --num-points {npts} > deltas.log" \
    ]


    adp_file = runtime_meta_util.generate_adp(char_board,blk,loc,cfg)

    runtime_sec = 0
    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=char_board.full_model_number, \
                         npts=npts_spat_error)
        print(">> %s" % cmd)
        runtime_sec += runtime_meta_util.run_command(cmd)

    logger.log('upd_mdl',runtime_sec)

    runtime_meta_util.remove_file(adp_file)


'''
Do some initial bootstrapping to fit the elicited models.
'''
def bootstrap_block(logger,board,blk,loc,cfg,grid_size=9,num_samples=5):
    CMDS = [ \
             "python3 grendel.py characterize --adp {adp} --model-number {model} --grid-size {grid_size} --num-hidden-codes {num_samples} --adp-locs > characterize.log" \
            ]


    adp_file = runtime_meta_util.generate_adp(board,blk,loc,cfg)

    runtime_sec = 0
    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=board.full_model_number, \
                         grid_size=grid_size, \
                         num_samples=num_samples)
        print(">> %s" % cmd)
        runtime_sec += runtime_meta_util.run_command(cmd)

    logger.log('bootstrap',runtime_sec)

    runtime_meta_util.remove_file(adp_file)


def profile_block(logger,board,blk,loc,cfg,grid_size=9,calib_obj=llenums.CalibrateObjective.NONE):
    CMDS = [ \
             "python3 grendel.py prof {adp} --model-number {model} --grid-size {grid_size} {calib_obj} > profile.log" \
            ]

    adp_file = runtime_meta_util.generate_adp(board,blk,loc,cfg)

    runtime_sec = 0
    for CMD in CMDS:
        cmd = CMD.format(adp=adp_file, \
                         model=board.full_model_number, \
                         grid_size=grid_size, \
                         calib_obj=calib_obj.value)
        print(">> %s" % cmd)
        runtime_sec += runtime_meta_util.run_command(cmd)

    logger.log('profile',runtime_sec)
    runtime_meta_util.remove_file(adp_file)


def write_model_to_database(logger,pool,board,char_board):
    print("------- ")
    for idx,score in pool.meas_view.order_by_dominance():
        print("%d] %s" % (idx,str(score)))

    idx,score = pool.meas_view.get_best()

    code_values = pool.pool[idx]
    hidden_codes = dict(zip(pool.variables, \
                            code_values))

    new_config = pool.predictor.config.copy()
    for var,value in hidden_codes.items():
        new_config[var].value = value


    exp_delta_model_lib.remove_models(board, \
                                      ['block','loc','static_config','calib_obj'], \
                                      block=pool.predictor.block, \
                                      loc=pool.predictor.loc, \
                                      config=new_config,  \
                                      calib_obj=llenums.CalibrateObjective.MODELBASED)

    for dataset in exp_profile_dataset_lib.get_datasets(char_board, \
                                                        ['block','loc','static_config','hidden_config'], \
                                                        block=pool.predictor.block, \
                                                        loc=pool.predictor.loc, \
                                                        config=new_config):
        exp_profile_dataset_lib.update(board,dataset)


    print("##### BEST DELTAS ######")
    print(new_config)
    print("---------- codes and score ------")
    print(hidden_codes)
    print(score)
    print("-------- delta models ----------------")
    for model in exp_delta_model_lib.get_models(char_board, \
                                                ['block','loc','static_config','hidden_config'], \
                                                block=pool.predictor.block, loc=pool.predictor.loc, \
                                                config=new_config):
        model.calib_obj = llenums.CalibrateObjective.MODELBASED
        print(model)
        print("------------")
        exp_delta_model_lib.update(board,model)

    print("###################")
    print("")
    print("")

'''
This function takes a point and evaluates it in the hardware to identify
the delta model parameters. These labels are attached.
'''
def query_hidden_codes(logger,pool,board,blk,loc,cfg,hidden_codes,npts,grid_size=9):
    new_cfg = cfg.copy()
    for var,value in hidden_codes.items():
        int_value = blk.state[var].nearest_value(value)
        new_cfg[var].value = int_value

    for out in blk.outputs:
        exp_model = exp_delta_model_lib.ExpDeltaModel(blk,loc,out,new_cfg, \
                                                      n=npts, \
                                                      calib_obj=llenums.CalibrateObjective.NONE)
        exp_delta_model_lib.update(board,exp_model)

    profile_block(logger,board,blk,loc,new_cfg,grid_size)
    update_model(logger,board,blk,loc,new_cfg,npts)

    mdls = exp_delta_model_lib.get_models(board, \
                                          ['block','loc','static_config','hidden_config'], \
                                          block=blk,
                                          loc=loc,
                                          config=new_cfg)
    assert(len(mdls) > 0)
    variables = {}
    errors= {}
    for mdl in mdls:
        variables[mdl.output.name] = mdl.variables()
        errors[mdl.output.name] = mdl.model_error.errors()

    codes = dict(mdl.hidden_codes())
    actual_obj = pool.objectives.compute(variables,errors)
    pred_deltavars,pred_model_errors = pool.predictor.predict(codes)
    pred_obj = pool.objectives.compute(pred_deltavars,pred_model_errors)

    print("samp %s" % (codes))
    for i,(out,name,obj,tol,prio) in enumerate(pool.objectives):
        print("  %s obj=%s pred=%f meas=%f" % (name,obj,pred_obj.values[i],actual_obj.values[i]))


    assert(pool.has_code(codes))
    actual_score = pool .affix_label_to_code(codes,variables,errors)
    return actual_score

'''
Build the symbolic predictor from the transfer learning data
and the block specification
'''
def build_predictor(xfer_board,block,loc,config):
    predictor = predlib.Predictor(block,loc,config)
    obj = predlib.MultiOutputObjective()
    npts = None
    for output in block.outputs:
        phys_model = exp_phys_model_lib.load(xfer_board,block,config,output)
        npts = phys_model.model_error.n if npts is None else npts
        assert(npts == phys_model.model_error.n)
        if phys_model is None:
           raise Exception("no physical model for output <%s> of block <%s> under config <%s>" \
                           % (output.name,block.name,config.mode))
        for var,pmodel in phys_model.variables().items():
            predictor.set_variable(output,var,pmodel)

        predictor.set_model_error(output,phys_model.model_error)

        obj.add(output, output.deltas[config.mode].objective)
        for index,_ in phys_model.model_error.points(block):
            obj.add_error(output,index)


    return npts,obj,predictor

'''
Update the predictor parameters with the characterization data
'''
def update_predictor(predictor,char_board):
     for model in exp_delta_model_lib.get_all(char_board):
        hcs = dict(model.hidden_codes())
        for var,val in model.variables().items():
            predictor.add_variable_datapoint(model.output, var,  hcs, val)

        for index,input_values in model.model_error.points():
            val = model.model_error.get_error(input_values)
            predictor.add_error_datapoint(model.output, index,  hcs, val)


     predictor.fit()


def add_random_unlabelled_samples(pool,count,total=4000):
    npts = 0
    for constraint,score in samplelib.get_sample(pool,num_samples=2):
        if npts > count:
            return

        samp = pool.default_sample()
        for var,val in constraint.items():
            samp[var] = val

        if not pool.has_code(samp):
           pool.add_unlabeled_code(samp)
           npts += 1


####
# Block calibration routine
#
###
def calibrate_block(logger, \
                    board,xfer_board, \
                    block,loc,config, \
                    grid_size=9, \
                    num_iters=3, \
                    samples_per_round=5, \
                    rounds=1, \
                    max_samples=20):
    logger.set_configured_block(block,loc,config.mode)


    # get board with initial code pool
    char_model = runtime_meta_util.get_model(board,block,loc,config)
    char_board = runtime_util.get_device("%s-active-cal/%s"  \
                                         % (board.model_number,char_model),layout=False)
    # load physical models for transfer learning. Compute the number of parameters
    phys_models = {}

    # build a calibration objective predictor with per-variable models.
    npts_spat_err,objfun,predictor = build_predictor(xfer_board,block,loc,config)
    print("# spatial error points: %d" % npts_spat_err)
    nsamps_reqd = predictor.min_samples() + 1
    max_samples += nsamps_reqd

    # collect initial data for fitting the transfer model
    # and fit all of the initial guesses for the parameters on the transfer model
    # this should give us an initial predictor
    print("==== BOOTSTRAPPING <#samps=%d> ====" % nsamps_reqd)
    bootstrap_block(logger, \
                    char_board,block,loc,config, \
                    grid_size=grid_size, \
                    num_samples=nsamps_reqd)
    update_model(logger,char_board,block,loc,config,npts_spat_err)

    # fit all of the parameters in the predictor.
    update_predictor(predictor,char_board)

    # next, we're going to populate the initial pool of points.
    print("==== SETUP INITIAL POOL ====")
    code_pool= load_code_pool_from_database(char_board, predictor,objfun)

    if len(code_pool.pool) >= max_samples:
        write_model_to_database(logger,code_pool, board,char_board)
        return

    for rnd in range(rounds):
        #TODO: maybe put this in a loop?
        # fit all of the parameters in the predictor.
        print("==== UPDATING PREDICTOR [%d/%d] ====" % (rnd+1,rounds))
        predictor.clear()
        update_predictor(predictor,char_board)
        code_pool.update_predicted_labels()

        print("==== ADD UNLABELLED [%d/%d] ====" % (rnd+1, rounds))
        add_random_unlabelled_samples(code_pool,samples_per_round)

        print("==== QUERY UNLABELLED [%d/%d] ====" % (rnd+1,rounds))
        print("")
        for pred_score, hcs in code_pool.get_unlabeled():
            print("=> codes=%s" % hcs)
            actual_score = query_hidden_codes(logger,code_pool,char_board,block,loc,config,hcs, \
                               npts_spat_err, grid_size=grid_size)
            print("-----------")
            print("=> PRED   score=%s" % pred_score)
            print("=> ACTUAL score=%s" % actual_score)
            print("")

    write_model_to_database(logger,code_pool, board,char_board)

def calibrate(args):
    board = runtime_util.get_device(args.model_number)
    xfer_board = runtime_util.get_device(args.xfer_db)

    logger = ModelCalibrateLogger('actcal_%s.log' % args.model_number)


    if not args.adp is None:
        adp = runtime_util.get_adp(board,args.adp,widen=args.widen)
        for cfg in adp.configs:
            blk = board.get_block(cfg.inst.block)
            if not blk.requires_calibration():
                continue

            cfg_modes = cfg.modes
            for mode in cfg_modes:
                cfg.modes = [mode]

                calibrate_block(logger, \
                                board, \
                                xfer_board, \
                                blk,cfg.inst.loc,cfg, \
                                grid_size=args.grid_size, \
                                rounds=args.rounds, \
                                samples_per_round=args.samples_per_round, \
                                max_samples=args.max_samples)

    else:
        raise Exception("unimplemented")

