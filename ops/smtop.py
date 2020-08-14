from enum import Enum
import z3
import math

class Z3Ctx:
  def __init__(self,env,optimize):
    if optimize:
      self._solver = z3.Optimize()
    else:
      self._solver = z3.Solver()

    self._optimize = optimize
    self._z3vars = {}
    self._smtvars = {}
    self._smtenv = env
    self._sat = None
    self._model = None

  def sat(self):
    return self._sat

  def model(self):
    if self._sat:
      return self.translate(self._model)
    else:
      raise Exception("unsat: no model")

  def decl(self,typ,var):
    if typ == SMTEnv.Type.REAL:
      v = z3.Real(var)
    elif typ == SMTEnv.Type.BOOL:
      v = z3.Bool(var)
    elif typ == SMTEnv.Type.INT:
      v = z3.Int(var)
    else:
      raise Exception("????")

    self._z3vars[var] = v
    self._smtvars[v] = var

  def push(self):
    self._solver.push()

  def pop(self):
    self._solver.pop()

  def cstr(self,cstr):
    self._solver.add(cstr)

  def z3var(self,name):
    assert(isinstance(name,str))
    if not name in self._z3vars:
      for v in self._z3vars.keys():
        print("var %s" % v)

      raise Exception("not declared: <%s>" % str(name))

    return self._z3vars[name]

  def translate(self,model):
    assigns = {}
    for v in self._z3vars.values():
      smtvar = self._smtvars[v]
      value = model[v]
      if value is None:
        unboxed = None
      elif isinstance(value,z3.IntNumRef):
        unboxed = value.as_long()
      elif isinstance(value,z3.BoolRef):
        if str(value) == 'True':
          unboxed = True
        else:
          unboxed = False
      elif isinstance(value,z3.RatNumRef):
        fltstr = value.as_decimal(12).split('?')[0]
        unboxed = float(str(fltstr))
      else:
        raise Exception("unknown class <%s> " % (model[v].__class__.__name__))

      assigns[smtvar] = unboxed

    return assigns

  def optimize(self,z3expr,minimize=True):
    rmap = {
      'unsat': False,
      'unknown': False,
      'sat': True
    }
    assert(self._optimize)
    h = self._solver.minimize(z3expr)
    result = self._solver.check()
    self._sat = rmap[str(result)]
    if self.sat():
      minval = self._solver.lower(h)
      fltstr = minval.as_decimal(12).split('?')[0]
      unboxed = float(str(fltstr))
      m = self._solver.model()
      self._model = m
      return self.translate(m)


  def solve(self):
    rmap = {
      'unsat': False,
      'unknown': False,
      'sat': True
    }
    result = self._solver.check()
    #print("result: %s" % result)
    self._sat = rmap[str(result)]
    #print("sat: %s" % self._sat)
    if self.sat():
      m = self._solver.model()
      self._model = m
      return self.translate(m)

  def negate_model(self,model):
    clauses = []
    for v in self._z3vars.values():
      if z3.is_bool(v):
        value = model[v]
        clauses.append(value != v)

    self.cstr(z3.Or(clauses))

  def next_solution(self):
    assert(self._sat)
    self.negate_model(self._model)

class SMTEnv:
  class Type(Enum):
    REAL = "Real"
    BOOL = "Bool"
    INT = "Int"

  def __init__(self):
    self._decls = []
    self._cstrs = []
    self._vars = []

  def num_vars(self):
    return len(self._to_smtvar)

  def num_cstrs(self):
    return len(self._cstrs)


  def decl(self,name,typ):
    if name in self._vars:
      return

    assert(isinstance(typ, SMTEnv.Type))
    self._vars.append(name)
    self._decls.append(SMTDecl(name,typ))

  def eq(self,e1,e2):
    self._cstrs.append(SMTAssert(SMTEq(e1,e2)))

  def lt(self,e1,e2):
    self._cstrs.append(SMTAssert(SMTLT(e1,e2)))

  def lte(self,e1,e2):
    self._cstrs.append(SMTAssert(SMTLTE(e1,e2)))

  def gte(self,e1,e2):
    self.lte(e2,e1)

  def gt(self,e1,e2):
    self.lt(e2,e1)

  def cstr(self,c):
    self._cstrs.append(SMTAssert(c))

  def to_z3(self,optimize=None):
    ctx = Z3Ctx(self,optimize=not optimize is None)
    for decl in self._decls:
      decl.to_z3(ctx)

    for cstr in self._cstrs:
      cstr.to_z3(ctx)

    if not optimize is None:
      z3opt = optimize.to_z3(ctx)
    else:
      z3opt = None

    return ctx,z3opt

  def to_smtlib2(self):
    prog = ""
    for decl in self._decls:
      prog += ("%s\n" % decl.to_smtlib2())

    for cstr in self._cstrs:
      prog += ("%s\n" % cstr.to_smtlib2())

    prog += "(check-sat)\n"
    prog += "(get-model)\n"
    prog += "(exit)\n"
    return prog

class SMTOp:
  def __init__(self):
    pass

  def __repr__(self):
    return self.to_smtlib2()

class SMTVar(SMTOp):

  def __init__(self,name):
    assert(isinstance(name,str))
    SMTOp.__init__(self)
    self._name = name

  def to_smtlib2(self):
    return "%s" % str(self._name)

  def to_z3(self,ctx):
    return ctx.z3var(self._name)

class SMTConst(SMTOp):

  def __init__(self,value):
    SMTOp.__init__(self)
    self._value = value

  def to_z3(self,ctx):
    return self._value

  def to_smtlib2(self):
    return "%f" % self._value

class SMTMult(SMTOp):

  def __init__(self,e1,e2):
    SMTOp.__init__(self)
    self._arg1 = e1
    self._arg2 = e2

  def to_z3(self,ctx):
    return self._arg1.to_z3(ctx)*self._arg2.to_z3(ctx)

  def to_smtlib2(self):
    return "(* %s %s)" % \
      (self._arg1.to_smtlib2(),
       self._arg2.to_smtlib2())


class SMTLeftShift(SMTOp):
  def __init__(self,e1,e2):
    SMTOp.__init__(self)
    self._arg1 = e1
    self._arg2 = e2

  def to_z3(self,ctx):
    return z3.self._arg1.to_z3(ctx)<<self._arg2.to_z3(ctx)


  def to_smtlib2(self):
    return "(<< %s %s)" % \
      (self._arg1.to_smtlib2(),
       self._arg2.to_smtlib2())


class SMTAdd(SMTOp):
  def __init__(self,e1,e2):
    SMTOp.__init__(self)
    self._arg1 = e1
    self._arg2 = e2

  def to_z3(self,ctx):
    return self._arg1.to_z3(ctx)+self._arg2.to_z3(ctx)


  def to_smtlib2(self):
    return "(+ %s %s)" % \
      (self._arg1.to_smtlib2(),
       self._arg2.to_smtlib2())

class SMTDecl(SMTOp):

  def __init__(self,name,t):
    SMTOp.__init__(self)
    self._name = name
    self._type = t

  def to_z3(self,ctx):
    ctx.decl(self._type,self._name)

  def to_smtlib2(self):
    return "(declare-const %s %s)"  \
      % (self._name,self._type.value)

class SMTNot(SMTOp):

  def __init__(self,e1):
    SMTOp.__init__(self)
    self._arg = e1

  def to_z3(self,ctx):
    return z3.Not(self._arg.to_z3(ctx))


  def to_smtlib2(self):
    return "(not %s)"  \
      % (self._arg.to_smtlib2())

class SMTOr(SMTOp):

  def __init__(self,e1,e2):
    SMTOp.__init__(self)
    self._arg1 = e1
    self._arg2 = e2

  def to_z3(self,ctx):
    return z3.Or(self._arg1.to_z3(ctx), self._arg2.to_z3(ctx))


  def to_smtlib2(self):
    return "(or %s %s)"  \
      % (self._arg1.to_smtlib2(),
         self._arg2.to_smtlib2())



class SMTAnd(SMTOp):

  def __init__(self,e1,e2):
    SMTOp.__init__(self)
    self._arg1 = e1
    self._arg2 = e2

  def to_z3(self,ctx):
    return z3.And(self._arg1.to_z3(ctx), self._arg2.to_z3(ctx))


  def to_smtlib2(self):
    return "(and %s %s)"  \
      % (self._arg1.to_smtlib2(),
         self._arg2.to_smtlib2())


class SMTEq(SMTOp):

  def __init__(self,e1,e2):
    SMTOp.__init__(self)
    assert(isinstance(e1,SMTOp))
    assert(isinstance(e2,SMTOp))
    self._arg1 = e1
    self._arg2 = e2

  def to_z3(self,ctx):
    return self._arg1.to_z3(ctx) == self._arg2.to_z3(ctx)


  def to_smtlib2(self):
    return "(= %s %s)"  \
      % (self._arg1.to_smtlib2(),
         self._arg2.to_smtlib2())


class SMTLT(SMTOp):

  def __init__(self,e1,e2):
    SMTOp.__init__(self)
    assert(isinstance(e1,SMTOp))
    assert(isinstance(e2,SMTOp))
    self._arg1 = e1
    self._arg2 = e2

  def to_z3(self,ctx):
    return self._arg1.to_z3(ctx) < self._arg2.to_z3(ctx)

  def to_smtlib2(self):
    return "(< %s %s)"  \
      % (self._arg1.to_smtlib2(),
         self._arg2.to_smtlib2())


class SMTAtMostN(SMTOp):

  def __init__(self,vs,n):
    SMTOp.__init__(self)
    self._vars = vs
    self._n = n

  def to_z3(self,ctx):
    args = list(map(lambda v: (ctx.z3var(v),1), self._vars))
    return z3.PbLe(args,self._n)

  def to_smtlib2(self):
    args = self._vars
    argstr = " ".join(args)
    typstr = " ".join(map(lambda i: '1', \
                          range(1,len(args)+1)))
    return "((_ pble %s %d) %s)"  \
      % (typstr,self._n,argstr)



class SMTExactlyN(SMTOp):

  def __init__(self,vs,n):
    SMTOp.__init__(self)
    self._vars = vs
    self._n = n

  def to_z3(self,ctx):
    args = list(map(lambda v: (ctx.z3var(v),1), self._vars))
    return z3.PbEq(args,self._n)

  def to_smtlib2(self):
    args = self._vars
    argstr = " ".join(args)
    typstr = " ".join(map(lambda i: '1', \
                          range(1,len(args)+1)))
    return "((_ pbeq %s %d) %s)"  \
      % (typstr,self._n,argstr)


class SMTAssert(SMTOp):

  def __init__(self,cstr):
    SMTOp.__init__(self)
    assert(isinstance(cstr,SMTOp))
    assert(not isinstance(cstr,SMTConst))
    self._cstr = cstr

  def to_z3(self,ctx):
    ctx.cstr(self._cstr.to_z3(ctx))

  def to_smtlib2(self):
    return "(assert %s)"  \
      % (self._cstr.to_smtlib2())


class SMTImplies(SMTOp):

  def __init__(self,e1,e2):
    SMTOp.__init__(self)
    assert(isinstance(e1,SMTOp))
    assert(isinstance(e2,SMTOp))
    self._arg1 = e1
    self._arg2 = e2

  def to_z3(self,ctx):
    return z3.Implies(self._arg1.to_z3(ctx),
                      self._arg2.to_z3(ctx))

  def to_smtlib2(self):
    return "(implies %s %s)"  \
      % (self._arg1.to_smtlib2(),
         self._arg2.to_smtlib2())


class SMTLTE(SMTOp):

  def __init__(self,e1,e2):
    assert(isinstance(e1,SMTOp))
    assert(isinstance(e2,SMTOp))
    SMTOp.__init__(self)
    self._arg1 = e1
    self._arg2 = e2

  def to_z3(self,ctx):
    return self._arg1.to_z3(ctx) <= self._arg2.to_z3(ctx)

  def to_smtlib2(self):
    return "(<= %s %s)"  \
      % (self._arg1.to_smtlib2(),
         self._arg2.to_smtlib2())


def SMTBidirImplies(c1,c2):
  return SMTAnd(
    SMTImplies(c1,c2),
    SMTImplies(c2,c1)
  )

def SMTNeq(c1,c2):
  return SMTNot(SMTEq(c1,c2))

def SMTMapAdd(clauses):
  assert(len(clauses) > 0)
  clause = clauses[0]
  if len(clauses) == 1:
    return clause

  for next_clause in clauses[1:]:
    clause = SMTAdd(clause,next_clause)
  return clause


def SMTMapOr(clauses):
  assert(len(clauses) > 0)
  clause = clauses[0]
  if len(clauses) == 1:
    return clause

  for next_clause in clauses[1:]:
    clause = SMTOr(clause,next_clause)
  return clause


def SMTAllFalse(clauses):
  assert(len(clauses) > 0)
  clause = SMTNot(clauses[0])
  if len(clauses) == 1:
    return clause

  for next_clause in clauses[1:]:
    clause = SMTAnd(clause,SMTNot(next_clause))
  return clause

