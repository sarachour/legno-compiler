import runtime.runtime_util as runtime_util

import runtime.fit.model_fit as fitlib
import runtime.activecal_pass.predictor as predlib
import runtime.activecal_pass.hidden_code_pool as poollib
import runtime.activecal_pass.dominance as domlib

import itertools
import numpy as np
import random
import math

def multires_sample(free_vars,obj,pool,bounds={},max_points=8,select_top=0.10):
        values = {}
        resolutions = {}
        for var in free_vars:
                vals = pool.get_values(var)
                # if we're bounding this variable, only choose valuesin range
                if var in bounds:
                        l,u = bounds[var]
                        vals = list(filter(lambda v: v >= l and v <= u,vals))

                # if there are more values for this variable than the maximum allowed, reduce the resolution.
                if len(vals) > max_points:
                        step = math.ceil(len(vals)/max_points)
                        vals = list(map(lambda i: vals[i], range(0,len(vals),step)))
                        resolutions[var] = step
                else:
                        resolutions[var] = 0

                values[var] = vals

        # score all of the combinations
        options = list(map(lambda v: values[v], free_vars))
        scores = []
        assigns = []
        for combo in itertools.product(*options):
                vdict = dict(zip(free_vars,combo))
                score = obj.compute(vdict)
                assigns.append(vdict)
                scores.append(score)

        # sort from lowest to highest score
        indices = np.argsort(scores)
        # choose the top x% of items and find a higher resolution value.
        for i in range(round(len(indices)*select_top+1)):
                vdict = assigns[indices[i]]
                score = scores[indices[i]]
                print(vdict,score)
                bounds = {}
                has_higher_fidelity = False
                # set up the bounds for the finer resolution search and determine
                # if there is actually a finer resolution search to consider 
                for var,val in vdict.items():
                        all_vals = pool.get_values(var)
                        lower =max(val-resolutions[var],min(all_vals))
                        upper =min(val+resolutions[var],max(all_vals))
                        bounds[var] = (lower,upper)
                        has_higher_fidelity |= (resolutions[var] > 0)

                if has_higher_fidelity:
                  for score,vdict in multires_sample(free_vars,obj,pool, \
                                                           bounds=bounds, \
                                                           max_points=max_points, \
                                                           select_top=select_top):
                     yield score,vdict
                else:
                  yield score,vdict


def get_minimization_expr(pool):
        free_vars = []
        subobjs = []
        for idx,(out,name,obj,tol,prio) in enumerate(pool.objectives):
                conc_obj = pool.predictor.substitute(out,obj)
                free_vars += list(conc_obj.vars())
                subobjs.append(conc_obj)

        min_expr = pool.objectives.make_distance_expr(subobjs)
        variables = list(set(free_vars))
        return variables,min_expr

def grid_sample(free_vars,obj,pool,max_points=8,select_top=0.10):
        values = {}
        bounds = {}

        for var in free_vars:
                vals = pool.get_values(var)
                bounds[var] = (min(vals),max(vals))

                # if there are more values for this variable than the maximum allowed, reduce the resolution.
                if len(vals) > max_points:
                        step = math.ceil(len(vals)/max_points)
                        vals = list(map(lambda i: vals[i], range(0,len(vals),step)))

                values[var] = vals

        options = list(map(lambda v: values[v], free_vars))
        scores = []
        assigns = []
        for combo in itertools.product(*options):
                vdict = dict(zip(free_vars,combo))
                print(vdict)
                print(free_vars)
                result = fitlib.local_minimize_model(free_vars,obj,{},vdict,bounds=bounds)
                codes = result['values']
                score = result['objective_val']
                scores.append(score)
                assigns.append(codes)
                print(codes,score)


        input("continue?")
        indices = np.argsort(scores)
        for idx in indices:
                yield scores[idx],assigns[idx]

def get_sample(pool,num_samples=100,debug=True):
    # compute constraints over hidden codes
    values = []
    scores = []

    free_vars,min_obj_fun = get_minimization_expr(pool)
    # compute how many points to consider per variable for this resolutions
    max_points = 1600
    if len(free_vars) > 0:
            pts_per_level = max(2,math.ceil(max_points**(1/len(free_vars))))
    else:
            pts_per_level = max_points

    print("sampling pts=%d" % pts_per_level)
    for score,vdict in grid_sample(free_vars,min_obj_fun,pool, \
                                       max_points=pts_per_level, \
                                       select_top=0.01):
            scores.append(score)
            values.append(list(map(lambda fv: vdict[fv], free_vars)))

    index = np.argsort(scores)
    for idx in index:
            vdict = dict(zip(free_vars,values[idx]))
            yield vdict,scores[idx]
