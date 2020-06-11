from enum import Enum
import ops.base_op as oplib
import ops.generic_op as genoplib

class UnifyConstraint(Enum):
  CONSTANT = "const"
  NONE = "none"

def get_assoc(op,expr):
  if expr.op == op:
    args = []
    for arg in expr.args:
      args += get_assoc(op,arg)

    return args
  else:
    return [expr]


def separate(op,args):
  is_op = []
  not_op = []
  for arg in args:
    if arg.op == op:
      is_op.append(arg)
    else:
      not_op.append(arg)

  return is_op,not_op

def unify_mult(pat_expr,targ_expr,cstrs):
  def canonicalize(expr):
    args_const,args_expr= separate(oplib.OpType.CONST,
                                  get_assoc(oplib.OpType.MULT,expr))
    const_val = 1.0
    for arg in args_const:
      const_val *= arg.value

    return const_val,args_expr

  targ_coeff,targ_args = canonicalize(targ_expr)
  pat_coeff,pat_args = canonicalize(pat_expr)

  ratio = targ_coeff/pat_coeff
  if ratio != 1:
    targ_args.append(genoplib.Const(ratio))

  print(targ_args)
  print(pat_args)
  raise Exception("partition [%s] into %d partitions" % (targ_args, \
                                                         len(pat_args)))
def compatible_results(r1,r2):
  raise Exception("test if two sets of assignments are comaptible")

def combine_results(r1,r2):
  raise Exception("combine two result dictionaries")

def unify(pat_expr,targ_expr,cstrs):
  print("---")
  print("pattern: %s" % pat_expr)
  print("target: %s" % targ_expr)
  print("cstrs: %s" % cstrs)
  if not pat_expr.op == targ_expr.op:
    return

  funcs = []
  if pat_expr.op == oplib.OpType.EMIT:
    for result in unify(pat_expr.arg(0), \
                        targ_expr.arg(0), \
                        cstrs):
      yield result

  elif pat_expr.op == oplib.OpType.INTEG:
    results = []
    for result1 in unify(pat_expr.arg(0), \
                          targ_expr.arg(0), \
                          cstrs):
      results.append(result1)

    for result2 in  unify(pat_expr.arg(1), \
                          targ_expr.arg(1), \
                          cstrs):
      for result1 in results:
        if compatible_results(result2,result1):
          combine_results(result1,result2)

  elif pat_expr.op == oplib.OpType.MULT:
    unify_mult(pat_expr,targ_expr,cstrs)
  else:
    raise NotImplementedError
