from enum import Enum
import ops.base_op as oplib

class UnifyConstraint(Enum):
  CONSTANT = "const"
  NONE = "none"

def unify(pat_expr,targ_expr,cstrs):
  print("---")
  print("pattern: %s" % pat_expr)
  print("target: %s" % targ_expr)
  print("cstrs: %s" % cstrs)
  if not pat_expr.op == targ_expr.op:
    return

  funcs = []
  if pat_expr.op == oplib.OpType.EMIT:
    func = unify(pat_expr.arg(0), \
                 targ_expr.arg(0), \
                 cstrs)
    funcs.append(func)
  if pat_expr.op == oplib.OpType.INTEG:
    func1 = unify(pat_expr.arg(0), \
                 targ_expr.arg(0), \
                 cstrs)
    func2 = unify(pat_expr.arg(1), \
                 targ_expr.arg(1), \
                 cstrs)
    funcs.append(func1)
    funcs.append(func2)
  else:
    raise NotImplementedError

  for func in funcs:
    for result in func:
      yield result
