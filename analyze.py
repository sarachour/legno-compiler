import hwlib.physdb as physdb
import phys_model.model_fit as fitlib
import phys_model.visualize as vizlib
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import ops.opparse as opparse
import time
import target_block


def analyze_delta_models():
    dev = hcdclib.get_device()
    block, inst, cfg = target_block.get_block(dev)

    db = physdb.PhysicalDatabase('board6')
    params = {}
    inputs = {}
    for blk in physdb.get_by_block_instance(db, dev, block, inst, cfg=cfg):
        fitlib.fit_delta_model(blk)


def analyze_physical_models():
    dev = hcdclib.get_device()
    block, inst, cfg = target_block.get_block(dev)
    db = physdb.PhysicalDatabase('board6')
    params = {}
    inputs = {}
    model_errors = []
    # build data set from codes
    for blk in physdb.get_by_block_instance(db, dev, block, inst, cfg=cfg):
        for par, value in blk.delta_model.params.items():
            if not par in params:
                params[par] = []
            params[par].append(value)

        for hidden_code, value in blk.hidden_codes():
            if not hidden_code in inputs:
                inputs[hidden_code] = []
            inputs[hidden_code].append(value)

        model_errors.append(blk.delta_model.cost)

    # infer physical model parameters from dataset
    phys_models = physdb.get_physical_models(db, dev, block, inst, cfg=cfg)
    phys_models.clear()
    for param,phys_model in phys_models.delta_model_params:
        phys_params = phys_model.spec.params
        phys_rel = phys_model.spec.relation

        if len(params[param]) < len(phys_params):
           raise Exception("cannot fit physical model with <%d> params. Too few (%d) datapoints" \
                           % (len(phys_params),len(params[param])))
        dataset = {'inputs':inputs,'meas_mean':params[param]}
        result = fitlib.fit_model(phys_params, phys_rel, dataset)
        for par,value in result['params'].items():
           phys_model.bind(par,value)

    # infer model error parameters from dataset
    phys_params = phys_models.model_error.spec.params
    phys_rel = phys_models.model_error.spec.relation
    if len(model_errors) < len(phys_params):
            raise Exception("cannot fit physical model with <%d> params. Too few (%d) datapoints" \
                            % (len(phys_params),len(params[param])))
    dataset = {'inputs':inputs,'meas_mean':model_errors}
    result = fitlib.fit_model(phys_params, phys_rel, dataset)
    for par,value in result['params'].items():
        phys_models.model_error.bind(par,value)

    # update database
    phys_models.update()
    assert(phys_models.complete)

dev = hcdclib.get_device()
block, inst, cfg = target_block.get_block(dev)

db = physdb.PhysicalDatabase('board6')
# build up dataset
params = {}
inputs = {}
for blk in physdb.get_by_block_instance(db, dev, block, inst, cfg=cfg):
    fitlib.fit_delta_model(blk)
