from enum import Enum
import ops.base_op as oplib
import ops.generic_op as genoplib
import ops.lambda_op as lambdoplib
from itertools import chain, combinations
import sympy
import random

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

  def set_by_name(self,v,e):
    assert(isinstance(v,str))
    self._assignments[v] = (v,e)


  def add(self,v,e):
    assert(not v.name in self._assignments)
    assert(v.op == oplib.OpType.VAR)
    self._assignments[v.name] = (v,e)

  def get_by_name(self,name):
      assert(isinstance(name,str))
      v,e = self._assignments[name]
      return (v,e)

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
    st = ""
    for v,e in self._assignments.values():
        st += "%s=%s\n" % (v,e)
    return st

class UnifyConstraint(Enum):
  CONSTANT = "const"
  FUNCTION = "func"
  NONE = "none"
  SAMEVAR = "samevar"
  VARIABLE = "var"

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

from sympy.solvers import solve as sympy_solve

def sympy_unify_const(pat_expr,targ_expr):
    assert(len(pat_expr.vars()) <= 1)
    assert(len(targ_expr.vars()) == 0)
    targ_syms,pat_syms= {},{}
    pat_symexpr = lambdoplib.to_sympy(pat_expr,pat_syms)
    targ_symexpr = lambdoplib.to_sympy(targ_expr,targ_syms)
    symbols = list(targ_syms.values()) + list(pat_syms.values())
    try:
        result = sympy_solve(targ_symexpr - pat_symexpr, \
                             symbols,dict=True)
    except Exception as e:
        return False,None,None

    assign = result[0]
    if len(pat_expr.vars()) == 1:
        pat_var = pat_expr.vars()[0]
        const_val = genoplib.Const(assign[pat_syms[pat_var]])
        return True,genoplib.Var(pat_var),const_val
    else:
        print(assign)
        raise NotImplementedError

def sympy_equals(e1,e2):
    syms = {}
    e1_symexpr = lambdoplib.to_sympy(e1,syms)
    e2_symexpr = lambdoplib.to_sympy(e2,syms)
    result = sympy.simplify(e1_symexpr - e2_symexpr)
    return result == 0

def sympy_unify_rewrite(pat_expr,targ_expr,cstrs,blacklist={}):
    updated_blacklist = False
    deterministic = False
    def add_to_bl(wildvar,expr):
        assert(isinstance(wildvar,sympy.Wild))
        if not var.name in blacklist:
            blacklist[var.name] = []
        if not symexpr in blacklist[var.name]:
            blacklist[var.name].append(symexpr)
            updated_blacklist = True

    targ_syms,pat_syms= {},{}
    pat_symexpr = lambdoplib.to_sympy(pat_expr,pat_syms,wildcard=True, \
                                    blacklist=blacklist)
    targ_symexpr = lambdoplib.to_sympy(targ_expr,targ_syms)
    if isinstance(targ_symexpr,float):
        result = sympy_solve(targ_symexpr - pat_symexpr, \
                             symbols=list(pat_syms.values()),
                             dict=True)[0] \
                             if len(pat_syms) == 1 else None
        deterministic = True
    else:
        result = targ_symexpr.match(pat_symexpr)
    if result is None:
        return

    valid = True
    unif = Unification()
    for var,symexpr in result.items():
        try:
            expr = lambdoplib.from_sympy(sympy.simplify(symexpr))
            unif.add(genoplib.Var(var.name), expr)
        except lambdoplib.FromSympyFailed as e:
            add_to_bl(var,symexpr)
            valid = False
            continue

        cstr = cstrs[var.name] if var.name in cstrs else \
               UnifyConstraint.NONE

        if cstr == UnifyConstraint.CONSTANT \
            and expr.op != oplib.OpType.CONST:
            add_to_bl(var,symexpr)
            valid = False
        if cstr == UnifyConstraint.VARIABLE \
           and expr.op != oplib.OpType.VAR:
            add_to_bl(var,symexpr)
            valid = False
        if cstr == UnifyConstraint.SAMEVAR:
            raise NotImplementedError

    wildvar,symexpr = random.choice(list(result.items()))
    if valid:
        yield unif
        add_to_bl(wildvar,symexpr)

    if updated_blacklist and not deterministic:
        for unif in sympy_unify_rewrite(pat_expr,targ_expr,cstrs,blacklist):
            yield unif


def unify(pat_expr,targ_expr,cstrs):
    def targ_exact_match(op):
        if op == oplib.OpType.EMIT or \
           op == oplib.OpType.INTEG:
            return True
        else:
            return False

    def pat_exact_match(op):
        if op == oplib.OpType.INTEG:
            return True
        else:
            return False

    new_targ_expr = canonicalize_call(targ_expr)
    if not new_targ_expr is None:
        targ_expr = new_targ_expr

    new_pat_expr = canonicalize_call(pat_expr)
    if not new_pat_expr is None:
        pat_expr = new_pat_expr

    for result in sympy_unify_rewrite(pat_expr,targ_expr,cstrs):
        yield result
