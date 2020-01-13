from enum import Enum
import pulp

class ILPCtx:

  def __init__(self,env):
    self._solver = pulp.LpProblem("LP", pulp.LpMinimize)
    self._pulpvars = {}
    self._ilpenv = env
    self._status = None

  def optimal(self):
    status = pulp.LpStatus[self._solver.status]
    return status == 'Optimal'

  def decl(self,typ,var):
    if typ == ILPEnv.Type.BOOL:
      v = pulp.LpVariable(var,
                          lowBound=0,
                          upBound=1,
                          cat='Integer')

    else:
      raise Exception("????")

    self._pulpvars[var] = v

  def pulp_var(self,name):
    if not name in self._pulpvars:
      for v in self._pulpvars.keys():
        print(v)

      raise Exception("not declared: <%s>" % str(name))

    return self._pulpvars[name]



  def cstr(self,cstr):
    self._solver += cstr

  def objfun(self,obj):
    self._solver += obj

  def translate(self):
    result = {}
    for v in self._solver.variables():
      jvar = self._ilpenv.from_ilpvar(v.name)
      if jvar is None:
        continue
      value = v.varValue
      result[jvar] = value
    return result

  def solve(self):
    self._solver.solve()
    status = pulp.LpStatus[self._solver.status]
    return self.translate()

class ILPEnv:

  class Type(Enum):
    BOOL = "Bool"

  def __init__(self):
    self._decls = []
    self._cstrs = []
    self._index = 0
    self._to_ilpvar = {}
    self._from_ilpvar = {}
    self._tempvar = 0
    self._objfun = None
    self._fail_msg = []

  def fail(self,msg):
    print("fail: %s" % msg)
    self.eq(ILPConst(0),ILPConst(1))

  def tempvar(self):
    v = self.decl("__temp%d" % self._tempvar,
                  ILPEnv.Type.BOOL)
    self._tempvar += 1
    self._ctx = None
    return v

  def set_objfun(self,o):
    self._objfun = o

  @property
  def ctx(self):
    return self._ctx

  def cstr(self,stmt):
    for cstr in stmt.compile():
      self._cstrs.append(cstr)

  def gte(self,e1,e2):
    self._cstrs.append(ILPLTE(e2,e1))

  def lte(self,e1,e2):
    self._cstrs.append(ILPLTE(e1,e2))

  def eq(self,e1,e2):
    self._cstrs.append(ILPEq(e1,e2))

  def num_tempvars(self):
    return self._tempvar

  def num_vars(self):
    return len(self._to_ilpvar)

  def num_cstrs(self):
    return len(self._cstrs)

  def to_model(self):
    ctx = ILPCtx(self)
    for decl in self._decls:
      decl.to_model(ctx)

    for cstr in self._cstrs:
      ctx.cstr(cstr.to_model(ctx))

    if not self._objfun is None:
      ctx.objfun(self._objfun.to_model(ctx))
    self._ctx = ctx
    return ctx


  def from_ilpvar(self,name):
    if name == '__dummy':
      return None
    return self._from_ilpvar[name]

  def has_ilpvar(self,name):
    return name in self._to_ilpvar

  def get_ilpvar(self,name):
    return self._to_ilpvar[name]


  def ilp_vars(self):
    return filter(lambda v: not '__temp' in v, \
                  self._to_ilpvar.keys())

  def decl(self,name,typ):
    if name in self._to_ilpvar:
      return self._to_ilpvar[name]

    assert(isinstance(typ, ILPEnv.Type))
    vname = "v%d" % self._index
    self._index += 1
    self._decls.append(ILPDecl(vname,typ))
    self._to_ilpvar[name] = vname
    self._from_ilpvar[vname] = name
    return vname


class ILPOp:
  def __init__(self):
    pass

class ILPVar(ILPOp):

  def __init__(self,name):
    ILPOp.__init__(self)
    self._name = name

  def to_model(self,ctx):
    return ctx.pulp_var(self._name)

class ILPConst(ILPOp):

  def __init__(self,value):
    ILPOp.__init__(self)
    self._value = value

  def to_model(self,ctx):
    return self._value

class ILPDecl(ILPOp):

  def __init__(self,name,t):
    ILPOp.__init__(self)
    self._name = name
    self._type = t

  def to_model(self,ctx):
    ctx.decl(self._type,self._name)

class ILPAdd(ILPOp):
  def __init__(self,es):
    ILPOp.__init__(self)
    self._args = es

  def compile(self):
    yield self

  def to_model(self,ctx):
    result = 0
    for arg in self._args:
      result += arg.to_model(ctx)
    return result

class ILPLTE(ILPOp):

  def __init__(self,e1,e2):
    assert(isinstance(e1,ILPOp))
    assert(isinstance(e2,ILPOp))
    ILPOp.__init__(self)
    self._arg1 = e1
    self._arg2 = e2

  def compile(self):
    yield self

  def to_model(self,ctx):
    return self._arg1.to_model(ctx) <= self._arg2.to_model(ctx)


def ILPMapAdd(clauses):
  assert(len(clauses) > 0)
  clause = clauses[0]
  if len(clauses) == 1:
    return clause

  else:
    return ILPAdd(clauses)

class ILPEq(ILPOp):


  def __init__(self,e1,e2):
    assert(isinstance(e1,ILPOp))
    assert(isinstance(e2,ILPOp))
    ILPOp.__init__(self)
    self._arg1 = e1
    self._arg2 = e2


  def to_model(self,ctx):
    return self._arg1.to_model(ctx) == self._arg2.to_model(ctx)


def ILPAndVar(ilpenv, bool1, bool2):
  # Z1 and Z2
  # Z3 ≤ Z1
  # Z3 ≤ Z2
  # Z3 + 1 ≥ Z1 + Z2
  tempvar = ilpenv.tempvar()
  ilpenv.cstr(ILPLTE(ILPVar(tempvar), bool1))
  ilpenv.cstr(ILPLTE(ILPVar(tempvar), bool2))
  ilpenv.cstr(ILPLTE(
    ILPAdd([bool1,bool2]), \
    ILPAdd([ILPVar(tempvar), ILPConst(1)])
  ))
  return tempvar
