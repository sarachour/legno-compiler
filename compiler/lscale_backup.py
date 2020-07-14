import util.util as util

import ops.scop as scop
import ops.op as ops
import ops.interval as interval

import hwlib.model as hwmodel
import hwlib.props as props
from hwlib.adp import AnalogDeviceProg


import compiler.common.prop_interval as prop_interval

import compiler.lscale_pass.lscale_util as lscale_util
import compiler.lscale_pass.lscale_common as lscale_common
import compiler.lscale_pass.scenv as scenvlib
import compiler.lscale_pass.scenv_gpkit as scenv_gpkit
import compiler.lscale_pass.scenv_linear as scenv_linear
import compiler.lscale_pass.scenv_smt as scenv_smt

import compiler.lscale_pass.expr_visitor as exprvisitor
import compiler.lscale_pass.lscale_util as lscale_util
import compiler.lscale_pass.lscale_common as lscale_common
import compiler.lscale_pass.lscale_infer as lscale_infer
import compiler.lscale_pass.lscale_physlog as lscale_physlog
from compiler.lscale_pass.objective.obj_mgr import LScaleObjectiveFunctionManager



def report_missing_models(model,circ):
    for block,loc,port,comp_mode,scale_mode in hwmodel.ModelDB.MISSING:
        lscale_physlog.log(circ,block,loc, \
                          comp_mode,
                          scale_mode)
        msg = "NO model: %s[%s].%s %s %s error" % \
              (block,loc,port, \
               comp_mode,scale_mode)

def scale(prog,adp,nslns, \
          model, \
          mdpe, \
          mape, \
          vmape, \
          mc, \
          ignore_models=[], \
          max_freq_khz=None, \
          do_log=True, \
          test_existence=False):
    def gen_models(model):
        models = [model]
        #if model.uses_delta_model():
        #    models.append(model.naive_model())

        return models

    assert(isinstance(model,util.DeltaModel))
    prop_interval.clear_intervals(adp)
    prop_interval.compute_intervals(prog,adp)
    objs = LScaleObjectiveFunctionManager.basic_methods()
    n_missing = 0
    has_solution = False
    for this_model in gen_models(model):
        for obj in objs:
            for idx,adp in enumerate(lscale_infer.infer_scale_config(prog, \
                                                                     adp, \
                                                                     nslns, \
                                                                     model=this_model, \
                                                                     max_freq_khz=max_freq_khz, \
                                                                     ignore_models=ignore_models, \
                                                                     mdpe=mdpe, \
                                                                     mape=mape, \
                                                                     vmape=vmape, \
                                                                     obj_fun=obj, \
                                                                     mc=mc)):
                if test_existence:
                    has_solution = True
                    break

                #for this_model in gen_models(model):
                scenv = scenvlib.LScaleEnv(model=this_model, \
                                           max_freq_khz=max_freq_khz, \
                                           mdpe=mdpe, \
                                           mape=mape, \
                                           vmape=vmape, \
                                           mc=mc)
                yield idx,obj.name(),scenv.params.tag(),adp

            if test_existence:
                break


        if test_existence:
            break

    if test_existence:
        if has_solution:
            yield None

        if not do_log:
            return


    if do_log:
        print("logging missing models: %s" % do_log)
        pars = scenvlib.LScaleEnvParams(model=model,
                                        max_freq_khz=max_freq_khz, \
                                        mdpe=mdpe,
                                        mape=mape,
                                        vmape=vmape,
                                        mc=mc)
        report_missing_models(model,adp)
        lscale_physlog.save(pars.calib_obj)
        if not lscale_physlog.is_empty() and \
           model.uses_delta_model():
            raise Exception("must calibrate components")

        lscale_physlog.clear()
