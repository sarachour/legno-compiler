import ops.scop as scop
import ops.op as ops
import ops.interval as interval

import logging
import networkx as nx

logger = logging.getLogger('lscale')
logger.setLevel(logging.ERROR)
#logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('lscale.log')
fh.setLevel(logging.ERROR)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

def log_info(msg):
    logger.info(msg)

def log_warn(msg):
    logger.warn(msg)

def log_debug(msg):
    logger.debug(msg)

def cancel_signs(orig_lhs,orig_rhs):
    const1,expr1 = orig_lhs.factor_const()
    const2,expr2 = orig_rhs.factor_const()
    if const1 >= 0 and const2 >= 0:
        pass
    elif const1 <= 0 and const1 <= 0:
        const1 *= -1
        const2 *= -1
    else:
        log_info("[sign mismatch] %s OP %s" % (orig_lhs,orig_rhs))
        return False,orig_lhs,orig_rhs

    new_expr1 = scop.SCMult(scop.SCConst(const1),expr1)
    new_expr2 = scop.SCMult(scop.SCConst(const2),expr2)
    return True,new_expr1,new_expr2


def is_zero(v):
    return abs(v) < 1e-14


def same_sign(v1,v2):
    if v1 < 0 and v2 < 0:
        return True
    elif v1 > 0 and v2 > 0:
        return True
    else:
        return False

def lower_bound_constraint(jenv,expr,math_lower,hw_lower,annot):
    if is_zero(math_lower) and hw_lower <= 0:
        return
    elif is_zero(math_lower) and hw_lower > 0:
        return jenv.fail("(1) %s <= %s*%s impossible" % (hw_lower,math_lower,expr))
    elif is_zero(hw_lower) and math_lower >= 0:
        return
    elif is_zero(hw_lower) and math_lower < 0:
        return jenv.fail("(2) %s <= %s*%s impossible" % (hw_lower,math_lower,expr))

    assert(not is_zero(math_lower))
    assert(not is_zero(hw_lower))

    if same_sign(math_lower,hw_lower) and \
       math_lower > 0 and hw_lower > 0:
        jenv.gte(scop.SCMult(expr,scop.SCConst(math_lower)),
                 scop.SCConst(hw_lower),annot)

    elif same_sign(math_lower,hw_lower) and \
         math_lower < 0 and hw_lower < 0:
        jenv.lte(scop.SCMult(expr,scop.SCConst(-math_lower)),
                 scop.SCConst(-hw_lower),annot)

    elif not same_sign(math_lower,hw_lower) and \
         hw_lower < 0 and math_lower > 0:
        pass

    elif not same_sign(math_lower,hw_lower) and \
         hw_lower > 0 and math_lower < 0:
        log_info("[[fail]] dne A st: %s < A*%s [%s]" \
                 % (hw_lower,math_lower,annot))
        jenv.fail("(3) %s <= %s*%s impossible" \
                  % (hw_lower,math_lower,expr))
    else:
        raise Exception("uncovered lb: %s %s [%s]" % (math_lower,hw_lower,annot))


def upper_bound_constraint(jenv,expr,math_upper,hw_upper,annot):
    if is_zero(math_upper) and hw_upper >= 0:
        return

    elif is_zero(math_upper) and hw_upper < 0:
        return

    elif is_zero(hw_upper) and math_upper <= 0:
        return

    elif is_zero(hw_upper) and math_upper > 0:
        return jenv.fail("(1) %s*%s <= %s impossible [%s]" \
                         % (math_upper,expr,hw_upper,annot))

    assert(not is_zero(math_upper))
    assert(not is_zero(hw_upper))

    if same_sign(math_upper,hw_upper) and \
       math_upper > 0 and hw_upper > 0:
        jenv.lte(scop.SCMult(expr,scop.SCConst(math_upper)),
                 scop.SCConst(hw_upper),annot)

    elif same_sign(math_upper,hw_upper) and \
         math_upper < 0 and hw_upper < 0:
        jenv.gte(scop.SCMult(expr,scop.SCConst(-math_upper)),
                 scop.SCConst(-hw_upper),annot)

    elif not same_sign(math_upper,hw_upper) and \
         hw_upper > 0 and math_upper < 0:
        pass

    elif not same_sign(math_upper,hw_upper) and \
         hw_upper < 0 and math_upper > 0:
        print("[[fail]] dne A st: %s > A*%s" % (hw_upper,math_upper))
        return jenv.fail("(2) %s*%s <= %s impossible [%s]" % \
                         (math_upper,expr,hw_upper,annot))
    else:
        raise Exception("uncovered ub: %s %s" % (math_upper,hw_upper))


def in_interval_constraint(jenv,scale_expr,math_rng,hw_rng,annot):
    upper_bound_constraint(jenv,scale_expr, \
                            math_rng.upper,hw_rng.upper,annot)
    lower_bound_constraint(jenv,scale_expr, \
                            math_rng.lower,hw_rng.lower,annot)

def reduce_vars(jenv):
    graph = nx.Graph()

    varsets = []
    for v in jenv.variables(in_use=True):
        graph.add_node(v)

    for (_lhs,_rhs,_) in jenv.eqs():
        _,lhs = _lhs.factor_const()
        _,rhs = _rhs.factor_const()
        if lhs.op == jop.JOpType.VAR and \
           rhs.op == jop.JOpType.VAR:
            graph.add_node(lhs.name)
            graph.add_node(rhs.name)
            graph.add_edge(lhs.name,rhs.name)

    for subg in nx.connected_components(graph):
        varsets.append(subg)


    return varsets

