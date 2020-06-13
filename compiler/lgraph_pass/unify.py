from enum import Enum
import ops.base_op as oplib
import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
from itertools import chain, combinations

def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

class Unification:

  def __init__(self):
    self._assignments = {}

  @property
  def assignments(self):
    return self._assignments.values()

  def add(self,v,e):
    assert(not v.name in self._assignments)
    assert(v.op == oplib.OpType.VAR)
    self._assignments[v.name] = (v,e)

  def compatible(self,unif2):
    for v in filter(lambda v: v in unif2._assignments, \
                    self._assignments.keys()):
      if self._assignments[v] != unif2.assignments[v]:
        return False
    return True

  def combine(self,u2):
    u = Unification()
    for v,e in self._assignments.values():
      u.add(v,e)
    for v,e in u2._assignments.values():
      u.add(v,e)
    return u

  def __repr__(self):
    return str(self._assignments.values())

class UnifyConstraint(Enum):
  CONSTANT = "const"
  FUNCTION = "func"
  NONE = "none"

class UnifyTable:

  def to_key(self,indices):
    return ",".join(map(lambda idx: str(idx),indices))

  def __init__(self,pattern_exprs,target_exprs,associative=False):
    self.unifs = {}
    self.pat_exprs = pattern_exprs
    self.target_exprs = target_exprs
    # any subset of target arguments can be assigned to pattern
    if associative:
      subsets = list(powerset(range(0,len(target_exprs))))
      for idx,pat in enumerate(pattern_exprs):
        self.unifs[idx] = {}
        for subset in subsets:
          if len(subset) == 0:
            continue

          args = list(map(lambda i: target_exprs[i],subset))
          self.unifs[idx][self.to_key(subset)] = {'indices':list(subset), \
                                                  'target_args':args, \
                                                  'unifications':[]}
    # 1-to-1 relationship
    else:
      assert(len(pattern_exprs) == len(target_exprs))
      for idx,pat in enumerate(pattern_exprs):
        self.unifs[idx] = {}
        self.unifs[idx][self.to_key([idx])] = {'indices':[idx], \
                                          'target_args':[target_exprs[idx]],
                                          'unifications':[]}

  def iterate(self):
    for i in self.unifs:
      pat = self.pat_exprs[i]
      for key,data in self.unifs[i].items():
        yield pat,data['target_args'],data['unifications']


  def solutions(self,allow_empty=True):
    def helper(pat_idx,targ_indices,unif):
      if pat_idx >= len(self.pat_exprs):
        if len(targ_indices) == 0:
          yield unif
        return

      for sln in self.unifs[pat_idx].values():
        # repeated term
        if any(filter(lambda idx : not idx in targ_indices, \
                   sln['indices'])):
          continue

        new_indices = list(filter(lambda idx: not idx in sln['indices'], \
                             targ_indices))
        for cand_unif in sln['unifications']:
          if unif.compatible(cand_unif):
            for result in helper(pat_idx+1,new_indices, \
                                unif.combine(cand_unif)):
              yield result

    if not allow_empty:
      for idx,results in self.unifs.items():
        if len(results.keys()) == 0:
          return

    unif = Unification()
    for result in helper(0,list(range(0,len(self.target_exprs))),unif):
      yield result


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


def canonicalize_call(expr):
  call_expr = None
  if expr.op == oplib.OpType.MULT:
    args_const,args_exprs= separate(oplib.OpType.CONST,
                                   get_assoc(oplib.OpType.MULT,expr))
    const_val = 1.0
    for arg in args_const:
      const_val *= arg.value


    if len(args_exprs) == 1 and \
       args_exprs[0].op == oplib.OpType.CALL:
      call_expr = args_exprs[0]
      func_expr = call_expr.func
      new_impl = genoplib.Mult(genoplib.Const(const_val), \
                               func_expr.expr)
      return genoplib.Call(call_expr.values, \
                           lambdoplib.Func(func_expr.func_args, \
                                           new_impl))
  else:
    return None

def canonicalize_sum(expr):
  args_const,args_expr= separate(oplib.OpType.CONST,
                                get_assoc(oplib.OpType.ADD,expr))
  const_val = 0.0
  for arg in args_const:
    const_val += arg.value

  return const_val,args_expr

def canonicalize_mult(expr):
  args_const,args_expr= separate(oplib.OpType.CONST,
                                get_assoc(oplib.OpType.MULT,expr))
  const_val = 1.0
  for arg in args_const:
    const_val *= arg.value

  return const_val,args_expr

def mkadd(args):
  if len(args) >= 2:
    return genoplib.Add(args[0],mkadd(args[1:]))
  elif len(args) == 1:
    return args[0]
  else:
    raise Exception("not implemented")


def mkmult(args):
  if len(args) >= 2:
    return genoplib.Mult(args[0],mkmult(args[1:]))
  elif len(args) == 1:
    return args[0]
  else:
    raise Exception("not implemented")

def unify_sum(pat_expr,targ_expr,cstrs):
  targ_offset,targ_args = canonicalize_sum(targ_expr)
  pat_offset,pat_args = canonicalize_sum(pat_expr)

  offset = targ_offset-pat_offset
  if offset != 0.0:
    targ_args.append(genoplib.Const(ratio))

  table = UnifyTable(pat_args,targ_args,associative=True)
  for pat_arg,targ_args,unifs in table.iterate():
    targ_expr = mkadd(targ_args)
    for unif in (unify(pat_arg,targ_expr,cstrs)):
      unifs.append(unif)

  for unif in table.solutions():
    yield unif


def unify_mult(pat_expr,targ_expr,cstrs):
  targ_coeff,targ_args = canonicalize_mult(targ_expr)
  pat_coeff,pat_args = canonicalize_mult(pat_expr)

  ratio = targ_coeff/pat_coeff
  if ratio != 1:
    targ_args.append(genoplib.Const(ratio))

  table = UnifyTable(pat_args,targ_args,associative=True)
  for pat_arg,targ_args,unifs in table.iterate():
    targ_expr = mkmult(targ_args)
    for unif in (unify(pat_arg,targ_expr,cstrs)):
      unifs.append(unif)

  for unif in table.solutions():
    yield unif



def unify(pat_expr,targ_expr,cstrs):
  #print("---")
  #print("pattern: %s" % pat_expr)
  #print("target: %s" % targ_expr)
  #print("cstrs: %s" % cstrs)

  funcs = []
  if pat_expr.op == oplib.OpType.VAR:
    var_cstr = cstrs[pat_expr.name]
    if var_cstr == UnifyConstraint.NONE:
      unif = Unification()
      unif.add(pat_expr,targ_expr)
      yield unif

    elif var_cstr == UnifyConstraint.CONSTANT and \
         targ_expr.op == oplib.OpType.CONST:
      unif = Unification()
      unif.add(pat_expr,targ_expr)
      yield unif

    elif var_cstr == UnifyConstraint.FUNCTION:
      unif = Unification()
      unif.add(pat_expr,targ_expr)
      yield unif


    return

  elif pat_expr.op == oplib.OpType.MULT:
    pass
  elif pat_expr.op == oplib.OpType.CALL:
    targ_expr = canonicalize_call(targ_expr)
    if targ_expr is None:
      return

  elif not pat_expr.op == targ_expr.op:
    return

  if pat_expr.op == oplib.OpType.EMIT:
    for result in unify(pat_expr.arg(0), \
                        targ_expr.arg(0), \
                        cstrs):
      yield result

  elif pat_expr.op == oplib.OpType.INTEG:
    results = []

    table = UnifyTable(pat_expr.args, \
                       targ_expr.args, \
                       associative=False)
    for pat_arg,targ_args,unifs in table.iterate():
      assert(len(targ_args) == 1)
      for unif in unify(pat_arg,targ_args[0],cstrs):
        unifs.append(unif)

    for unif in table.solutions():
      yield unif


  elif pat_expr.op == oplib.OpType.ADD:
    for unif in unify_sum(pat_expr,targ_expr,cstrs):
      yield unif

  elif pat_expr.op == oplib.OpType.MULT:
    for unif in unify_mult(pat_expr,targ_expr,cstrs):
      yield unif

  elif pat_expr.op == oplib.OpType.CALL:
    if len(pat_expr.values) != len(targ_expr.values):
      return

    table = UnifyTable(pat_expr.values + [pat_expr.func], \
                       targ_expr.values + [targ_expr.func], \
                       associative=False)
    for pat_arg,targ_args,unifs in table.iterate():
      assert(len(targ_args) == 1)
      for unif in unify(pat_arg,targ_args[0],cstrs):
        unifs.append(unif)

    for unif in table.solutions():
      yield unif


  elif pat_expr.op == oplib.OpType.FUNC:
    if len(pat_expr.func_args) != len(targ_expr.func_args):
      return

    # make replacement dictionary
    repl = dict(map(lambda repl: (repl[0],genoplib.Var(repl[1])), \
                zip(targ_expr.func_args,pat_expr.func_args)))
    new_impl = targ_expr.expr.substitute(repl)
    for result in unify(pat_expr.expr, \
                        new_impl, \
                        cstrs):
      yield result


  else:
    raise Exception("unhandled: %s" % pat_expr)
