import ops.base_op as baseoplib
import ops.generic_op as genoplib
import ops.op as oplib

'''
Factor out a constant coefficient from an expression. Return the base expression
and the constant coefficient.
'''
def get_expr_coefficient(expr):
  if expr.op == baseoplib.OpType.INTEG:
    return 1.0,expr
  elif expr.op == baseoplib.OpType.MULT:
    c1,e1 = get_expr_coefficient(expr.arg(0))
    c2,e2 = get_expr_coefficient(expr.arg(1))
    if e1 is None and e2 is None:
      return c1*c2,genoplib.Const(1.0)
    elif e1 is None:
      return c1*c2,e2
    elif e2 is None:
      return c1*c2,e1
    else:
      return c1*c2,genoplib.Mult(e1,e2)
  elif expr.op == baseoplib.OpType.ADD:
    c1,_e1 = get_expr_coefficient(expr.arg(0))
    c2,_e2 = get_expr_coefficient(expr.arg(1))
    e1 = genoplib.Const(1) if _e1 is None else _e1
    e2 = genoplib.Const(1) if _e2 is None else _e2
    if c1 == c2:
      return c1,genoplib.Add(e1,e2)
    else:
      return c1,genoplib.Add(e1,genoplib.Mult(genoplib.Const(c2/c1),e2))

  elif expr.op == baseoplib.OpType.CONST:
    return expr.value,None
  elif expr.op == baseoplib.OpType.VAR:
    return 1.0,expr
  elif expr.op == baseoplib.OpType.EMIT:
    c1,_e1 = get_expr_coefficient(expr.arg(0))
    return c1,genoplib.Emit(_e1,expr.loc)
  else:
    raise Exception("unhandled: %s" % expr)


'''
If there's any integration operation in the expression,
reshuffle terms so it is the toplevel node
'''
def canonicalize_integration_operation(expr):
  has_integ_op = any(map(lambda n: n.op == baseoplib.OpType.INTEG, expr.nodes()))
  if has_integ_op:
    if expr.op == baseoplib.OpType.MULT:
      c,e = get_expr_coefficient(expr)
      if(e.op == baseoplib.OpType.INTEG):
        return genoplib.Integ(
          genoplib.Mult(genoplib.Const(c),e.deriv),
          genoplib.Mult(genoplib.Const(c),e.init_cond)
        )
    elif expr.op == baseoplib.OpType.INTEG:
      return expr
    else:
      raise Exception("unhandled: %s" % expr)
  else:
    return expr
