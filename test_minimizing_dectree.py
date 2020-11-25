import json
import runtime.models.exp_phys_model as exp_phys_model_lib
import runtime.dectree.dectree_shrink as dectree_shrink_lib
import runtime.dectree.dectree_generalize as dectree_generalize_lib
import runtime.runtime_util as runtime_util

import hwlib.block as blocklib
import ops.interval as ivallib
import ops.generic_op as genoplib

tmpfile = "models.tmp"

def get_hidden_code_intervals(phys_model):
    intervals = {}
    for st in filter(lambda st: isinstance(st.impl,blocklib.BCCalibImpl), \
                     phys_model.block.state):
        minval = min(st.values)
        maxval = max(st.values)
        intervals[st.name] = ivallib.Interval(minval,maxval)

    return intervals

models = {}
with open(tmpfile,'r') as fh:
    dev = runtime_util.get_device('schar',layout=True)
    for line in fh:
        obj = json.loads(line)
        model = exp_phys_model_lib.ExpPhysModel.from_json(dev,obj)
        key = (model.block.name,model.static_cfg)
        if not key in models:
            models[key] = []
        models[key].append(model)

for key,mdls in models.items():
    if len(mdls) > 1:
        general_phys_model = dectree_generalize_lib.dectree_generalize(models[key])
    else:
        general_phys_model = models[key][0]

    intervals = get_hidden_code_intervals(general_phys_model)
    for varname,dectree in general_phys_model.variables().items():
        min_tree = dectree_shrink_lib.dectree_shrink(dectree,intervals)
        general_phys_model.set_variable(varname,min_tree)
