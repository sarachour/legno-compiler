import ops.interval as ivallib
import ops.generic_op as genoplib

def dectree_shrink(dectree,intervals,fractional_threshold=2e-2):
    shrunk_dectree = dectree.copy()

    # eliminate terms who don't pass a threshold
    for leaf in shrunk_dectree.leaves():
        assigns = dict(intervals)
        for par,val in leaf.params.items():
            assigns[par] = ivallib.Interval(val,val)

        model_range = ivallib.propagate_intervals(leaf.expr,assigns)
        offset,terms = genoplib.unpack_sum(leaf.expr)
        new_terms = [genoplib.Const(offset)]
        for term in terms:
            rng = ivallib.propagate_intervals(term,assigns)
            share_of_range = rng.bound / model_range.bound
            if share_of_range >= fractional_threshold:
                new_terms.append(term)


        leaf.expr = genoplib.sum(new_terms)
        new_params = {}
        for par,val in leaf.params.items():
            if par in leaf.expr.vars():
                new_params[par] = val
        leaf.params = new_params

    return shrunk_dectree
