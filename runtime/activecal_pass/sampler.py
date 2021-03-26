import runtime.runtime_util as runtime_util

import runtime.activecal_pass.predictor as predlib
import runtime.activecal_pass.hidden_code_pool as poollib
import runtime.activecal_pass.dominance as domlib

import itertools
import numpy as np

'''
check to see if two dictornies are compatible
'''
def sampler_compatible(prim,second):
        for v,val in second.items():
            assert(isinstance(val,int))
            if v in prim and prim[v] != val:
                assert(isinstance(prim[v],int))
                return False
        return True

'''
Helper function for finding compatible combinations of subobjective solutions
'''
def _sampler_iterate_over_samples(code_idx,offset,vdict,score,variables,values,scores,memos={}):
    if code_idx == len(variables):
        yield vdict,score
        return

    for idx in range(offset,len(values[code_idx])):
        curr_vdict = dict(zip(variables[code_idx], values[code_idx][idx]))

        # move to next
        if sampler_compatible(vdict,curr_vdict):
            vdict_next = dict(list(vdict.items()) + list(curr_vdict.items()))
            scores_next = list(score)
            scores_next.append(scores[code_idx][idx])

            for samp in _sampler_iterate_over_samples(\
                                                      code_idx+1, \
                                                      0, \
                                                      vdict_next, \
                                                      scores_next, \
                                                      variables, \
                                                      values, \
                                                      scores, \
                                                      memos):
                yield samp

'''
This function produces permutations of a list of indices. If the list of indices
is too long, it only permutes the first k elements of the array. It randomly selects k indices
to permute and put in the prefix of the array.
'''
def sampler_permute(indices,max_size=6,k=4,count=4000):
    if len(indices) <= max_size:
        for perm in itertools.permutations(indices):
            yield list(perm)

    else:
        for combo in itertools.combinations(indices,k):
            remainder = list(filter(lambda ind: not ind in combo,indices))
            for perm in itertools.permutations(combo):
                if count == 0:
                    return

                yield list(perm) + remainder
                count -= 1

def sampler_iterate_over_samples(objectives,variables,values,scores,num_samples=1):
    assert(isinstance(objectives, predlib.MultiOutputObjective))
    indices = list(range(len(values)))


    samples = []
    sample_scores = poollib.ParetoPoolView(objectives, 'samps')
    keys = []

    sampler_permute(indices)
    for perm in sampler_permute(indices,k=6):
        ord_variables = list(map(lambda idx: variables[idx],perm))
        ord_values = list(map(lambda idx: values[idx], perm))
        ord_scores = list(map(lambda idx: scores[idx], perm))

        n_samps = 0
        for samp,score in _sampler_iterate_over_samples(0,0,{},[], \
                                                        ord_variables,ord_values,ord_scores, \
                                                        memos={}):
            if n_samps >= num_samples:
                break

            # only add samples which haven't been seen before
            key = runtime_util.dict_to_identifier(samp)
            if key in keys:
                break

            # restructure score to invert permutation
            orig_score = [0]*len(indices)
            for idx in indices:
                orig_score[perm[idx]] = score[idx]

            # add the sample to the list of samples
            samples.append(samp)
            sample_scores.add(objectives.make_result(orig_score))
            keys.append(key)
            n_samps += 1

    indices = np.argsort(sample_scores.values)
    for idx in indices:
        samp = samples[idx]
        score = sample_scores.values[idx]
        print("%d] samp %s" % (idx,samp))
        print("   score=%s" % (str(score)))
        yield samp,score



def get_sample(pool,num_samples=100,debug=True):
    # compute constraints over hidden codes
    solutions = []
    solution_scores = []
    variables = []
    nobjs = len(list(pool.objectives))
    for idx,(out,name,obj,tol,prio) in enumerate(pool.objectives):
        # first derive a concrete expression for the subobjective
        # mapping hidden codes to objective function values
        if debug:
            print("-> processing objective %d (%s)" % (idx,obj))

        conc_obj = pool.predictor.substitute(out,obj)
        free_vars = list(conc_obj.vars())
        values = list(map(lambda v: pool.get_values(v), free_vars))
        options = list(itertools.product(*values))
        scores = []
        for vs in options:
                vdict = dict(zip(free_vars,vs))
                obj_val = conc_obj.compute(vdict)
                scores.append(obj_val)


        #write these data points to the collection of solutions
        indices = np.argsort(scores)
        variables.append(free_vars)
        solutions.append(list(map(lambda idx: list(options[idx]), indices)))
        solution_scores.append(list(map(lambda idx: scores[idx], indices)))

    if debug:
        print("===== Sample Counts ===")
        for idx,sln in enumerate(solutions):
            print("%d] %d variables=%s" % (idx,len(sln),str(variables[idx])))


    print("===== Produce Samples ===")
    for codes,score in sampler_iterate_over_samples(pool.objectives, \
                                                    variables,solutions,solution_scores, \
                                                    num_samples=num_samples):
        yield codes,score

