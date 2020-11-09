import ops.base_op as baseoplib
import ops.generic_op as genoplib
import ops.lambda_op as lambdaoplib
import ops.opparse as opparse
import parse

class NotHarmonizableError(Exception):

    def __init__(self,st):
        Exception.__init__(self,st)
        pass

global GAIN_ID
GAIN_ID = 0

def match_op(operator,exprs):
    for expr in exprs:
        if expr.op != operator:
            return False
    return True

def get_term(exprs,idx):
    op_type = exprs[0].op
    args = []
    for expr in exprs:
        assert(expr.op == op_type)
        args.append(expr.arg(idx))
    return args

def gain_var(idx):
    global GAIN_ID
    varname = (":gain(%d)" % idx)
    GAIN_ID += 1
    return varname

def from_gain_var(varname):
    parsed = parse.parse(":gain({:d})",varname)
    return int(parsed[0])

def is_gain_var(varname):
    return ":gain" in varname

def do_harmonize(baseline,deviations,modes):
    coeff,expr = genoplib \
                 .factor_positive_coefficient(baseline)
    new_gains = []
    new_modes = []
    gains = {}

    gain_var_name = gain_var(GAIN_ID)
    for mode,deviation in zip(modes,deviations):
        coeff_dev,expr_dev = genoplib \
                             .factor_positive_coefficient(deviation)
        if lambdaoplib.equivalent(expr,expr_dev):
            gain_value = coeff_dev/coeff
            gains[mode] = gain_value
        else:
            raise NotHarmonizableError("expressions not equal")

    master_expr = genoplib.Mult(genoplib.Var(gain_var_name),expr)
    return master_expr,[(gain_var_name,gains)]

def harmonizable(baseline,deviations,modes):
    try:
        master_expr,new_gains = do_harmonize(baseline,deviations,modes)
        return True
    except NotHarmonizableError:
        return False

def harmonize(baseline,deviations,modes):
    if harmonizable(baseline,deviations,modes):
        master_expr,gains_expr = \
                                 do_harmonize(baseline, \
                                              deviations, \
                                              modes)
        return master_expr,gains_expr

    if baseline.op == baseoplib.OpType.MULT and \
       match_op(baseoplib.OpType.MULT, deviations):
        master_expr1,gains_expr1 = \
            do_harmonize(baseline.arg(0), \
                     get_term(deviations,0),modes)
        master_expr2,gains_expr2 = \
            do_harmonize(baseline.arg(1), \
                     get_term(deviations,1),modes)
        gains_expr = gains_expr1 + gains_expr2
        return genoplib.Mult(master_expr1,master_expr2),gains_expr

    elif baseline.op == baseoplib.OpType.INTEG and \
         match_op(baseoplib.OpType.INTEG, deviations):
        master_expr1,gains_expr1 = \
            do_harmonize(baseline.arg(0), \
                     get_term(deviations,0),modes)
        master_expr2,gains_expr2 = \
            do_harmonize(baseline.arg(1), \
                     get_term(deviations,1),modes)
        gains_expr = gains_expr1 + gains_expr2
        return genoplib.Integ(master_expr1,master_expr2),gains_expr

    elif match_op(baseline.op, deviations):
        raise NotImplementedError

    else:
        raise NotHarmonizableError("cannot harmonize baseline and deviations")

def find_maximal_subset(baseline,deviations,modes):
    harmonizable = [False]*len(modes)
    for idx,(dev,mode) in enumerate(zip(deviations,modes)):
        try:
            harmonize(baseline,[dev],[mode])
            harmonizable[idx] = True
        except NotHarmonizableError:
            continue

    indices = list(filter(lambda idx: harmonizable[idx], \
                          range(0,len(modes))))
    modes_ = list(map(lambda idx: modes[idx], indices))
    deviations_ = list(map(lambda idx: deviations[idx], indices))
    return deviations_,modes_

def get_master_relation(baseline,all_deviations,all_modes):
    deviations,modes = find_maximal_subset(baseline,all_deviations,all_modes)
    assert(len(deviations) == len(modes))
    master,gains= harmonize(baseline,deviations,modes)
    return master,modes,gains
