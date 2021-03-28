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


def sampler_point_distance(normalization_info,vdict1,vdict2):
        dist = 0
        n = 0
        for k in filter(lambda k: k in vdict1, vdict2.keys()):
                dist += ((vdict1[k] - vdict2[k])/normalization_info[k])**2
                n += 1

        return math.sqrt(dist/n)


def sampler_objective_distance(multiobj, indices,partial_values):
        values = [1e-12]*len(multiobj)
        for i in range(len(indices)):
                values[indices[i]] = partial_values[i]

        res = multiobj.make_result(values)
        return res.distance()

# glues disparate samples together
def sampler_stitch_together(obj1,vdict1,obj2,vdict2,max_points=32):
        common_vars = []
        for k in filter(lambda k: k in vdict1, vdict2.keys()):
                common_vars.append(k)

        values = []
        pts_per_var= max(2,math.ceil(max_points**(1/len(common_vars))))
        for k in common_vars:
                lower = min(vdict1[k],vdict2[k])
                upper = max(vdict1[k],vdict2[k])
                step = max(1,math.ceil((upper-lower)/pts_per_var))
                values.append(list(range(lower,upper+1,step)))

        if len(common_vars) == 0:
                cdict = dict(list(vdict1.items()) + list(vdict2.items()))

                score1 = []
                for obj in obj1:
                        sc = obj.compute(cdict)
                        score1.append(sc)

                score2 = []
                for obj in obj2:
                        sc = obj.compute(cdict)
                        score2.append(sc)

                yield cdict,score1,score2
                return

        for combo in itertools.product(*values):
                cdict = dict(list(zip(common_vars,combo)) + \
                             list(filter(lambda tup: not tup[0] in common_vars, vdict1.items())) + \
                             list(filter(lambda tup: not tup[0] in common_vars, vdict2.items())) \
                )
                score1 = []
                for obj in obj1:
                        sc = obj.compute(cdict)
                        score1.append(sc)

                score2 = []
                for obj in obj2:
                        sc = obj.compute(cdict)
                        score2.append(sc)

                yield cdict,score1,score2

def sampler_overlapping(l1,l2):
        for it in l1:
                if it in l2:
                        return True

        return False


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

def get_sample(pool,num_samples=100,debug=True):
    # compute constraints over hidden codes
    values = []
    scores = []

    free_vars,min_obj_fun = get_minimization_expr(pool)
    # compute how many points to consider per variable for this resolutions
    max_points = 126000
    if len(free_vars) > 0:
            pts_per_level = max(2,math.ceil(max_points**(1/len(free_vars))))
    else:
            pts_per_level = max_points

    print("sampling pts=%d" % pts_per_level)
    for score,vdict in multires_sample(free_vars,min_obj_fun,pool, \
                                       max_points=pts_per_level, \
                                       select_top=0.001):
            scores.append(score)
            values.append(list(map(lambda fv: vdict[fv], free_vars)))

    index = np.argsort(scores)
    for idx in index:
            vdict = dict(zip(free_vars,values[idx]))
            yield vdict,scores[idx]
