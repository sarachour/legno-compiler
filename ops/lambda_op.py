from ops.base_op import *
import ops.generic_op as genop
import ops.interval as interval
import math

def to_python(e):
    if e.op == OpType.VAR:
        varname = "%s" % e.name
        return [varname],varname

    elif e.op == OpType.CONST:
        return [],"%.4e" % e.value

    elif e.op == OpType.ADD:
        vs1,a1 = to_python(e.arg1)
        vs2,a2 = to_python(e.arg2)
        v = list(set(vs1+vs2))
        return v,"(%s)+(%s)" % (a1,a2)

    elif e.op == OpType.POW:
        vs1,a1 = to_python(e.arg(0))
        vs2,a2 = to_python(e.arg(1))
        v = list(set(vs1+vs2))
        return v,"(%s)**(%s)" % (a1,a2)

    elif e.op == OpType.EXTVAR:
        return [],"0.0"

    elif e.op == OpType.MAX:
        vs1,a1 = to_python(e.arg(0))
        vs2,a2 = to_python(e.arg(1))
        v = list(set(vs1+vs2))
        return v,"max(%s,%s)" % (a1,a2)

    elif e.op == OpType.MIN:
        vs1,a1 = to_python(e.arg(0))
        vs2,a2 = to_python(e.arg(1))
        v = list(set(vs1+vs2))
        return v,"min(%s,%s)" % (a1,a2)

    elif e.op == OpType.MULT:
        vs1,a1 = to_python(e.arg1)
        vs2,a2 = to_python(e.arg2)
        v = list(set(vs1+vs2))
        return v,"(%s)*(%s)" % (a1,a2)

    elif e.op == OpType.CLAMP:
        v,a = to_python(e.arg1)
        ival = e.interval
        a2 = "max(%f,%s)" % (ival.lower,a)
        a3 = "min(%f,%s)" % (ival.upper,a2)
        return v,a3

    elif e.op == OpType.PAREN:
        v,a = to_python(e.arg(0))
        return v,"(%s)" % a

    elif e.op == OpType.ROUND:
        v1,a1 = to_python(e.arg(0))
        v2,a2 = to_python(e.arg(0))
        cmd = 'round({qty}/{step})*{step}'
        return v1+v2,cmd.format(qty=a1,step=a2)

    elif e.op == OpType.SGN:
        v,a = to_python(e.arg(0))
        return v,"math.copysign(1,%s)" % a

    elif e.op == OpType.SIN:
        v,a = to_python(e.arg(0))
        return v,"math.sin(%s.real)" % a

    elif e.op == OpType.COS:
        v,a = to_python(e.arg(0))
        return v,"math.cos(%s.real)" % a


    elif e.op == OpType.ABS:
        v,a = to_python(e.arg(0))
        return v,"abs(%s)" % a

    elif e.op == OpType.CALL:
        expr = e.func.expr
        args = e.func.func_args
        vals = e.values
        assigns = dict(zip(args,vals))
        conc_expr = expr.substitute(assigns)
        return to_python(conc_expr)

    elif e.op == OpType.EMIT:
        return to_python(e.arg(0))

    else:
        raise Exception("unimpl: %s" % e)


class Func(Op):
    def __init__(self, params, expr):
        Op.__init__(self,OpType.FUNC,[])
        self._expr = expr
        self._vars = params

    def compute(self,bindings):
        for v in self._vars:
            assert(v in bindings)

        return self._expr.compute(bindings)

    @property
    def expr(self):
        return self._expr

    @property
    def func_args(self):
        return self._vars

    def vars(self):
        bound = self._vars
        return list(filter(lambda v: not v in bound, \
                           self._expr.vars()))

    def substitute(self,args):
        subargs = {}
        for var in filter(lambda var: var in args, \
                          self.vars()):
            subargs[var] = args[var]

        expr = self.expr.substitute(subargs)
        return Func(self.func_args,expr)

    def to_json(self):
        obj = Op.to_json(self)
        obj['expr'] = self._expr.to_json()
        obj['vars'] = self._vars
        return obj

    @staticmethod
    def from_json(obj):
        expr = Op.from_json(obj['expr'])
        varnames = obj['vars']
        return Func(list(varnames),expr)

    def apply(self,values):
        assert(len(values) == len(self._vars))
        assigns = dict(zip(self._vars,values))
        return self._expr.substitute(assigns)

    def __repr__(self):
        pars = " ".join(map(lambda p: str(p), self._vars))
        return "lambd(%s).(%s)" % (pars,self._expr)


class Round(Op):

    def __init__(self,arg0,arg1):
        Op.__init__(self,OpType.ROUND,[arg0,arg1])

    def substitute(self,args):
        return Round(self.arg(0).substitute(args),
                   self.arg(1).substitute(args))

    def compute(self,bindings):
        a0 = self.arg(0).compute(bindings)
        a1 = self.arg(1).compute(bindings)
        return max(a0,a1)

    @staticmethod
    def from_json(obj):
        return Round( \
                    Op.from_json(obj['args'][0]),
                    Op.from_json(obj['args'][1]))


    def __repr__(self):
        return "round(%s,%s)" % (self.arg(0), \
                               self.arg(1))


class Max(Op):

    def __init__(self,arg0,arg1):
        Op.__init__(self,OpType.MAX,[arg0,arg1])

    def substitute(self,args):
        return Max(self.arg(0).substitute(args),
                   self.arg(1).substitute(args))

    def compute(self,bindings):
        a0 = self.arg(0).compute(bindings)
        a1 = self.arg(1).compute(bindings)
        return max(a0,a1)

    @staticmethod
    def from_json(obj):
        return Max( \
                    Op.from_json(obj['args'][0]),
                    Op.from_json(obj['args'][1]))


    def __repr__(self):
        return "max(%s,%s)" % (self.arg(0), \
                               self.arg(1))

class Min(Op):

    def __init__(self,arg0,arg1):
        Op.__init__(self,OpType.MIN,[arg0,arg1])

    def substitute(self,args):
        return Min(self.arg(0).substitute(args),
                   self.arg(1).substitute(args))

    def compute(self,bindings):
        a0 = self.arg(0).compute(bindings)
        a1 = self.arg(1).compute(bindings)
        return min(a0,a1)


    @staticmethod
    def from_json(obj):
        return Min( \
                    Op.from_json(obj['args'][0]),
                    Op.from_json(obj['args'][1]))


    def __repr__(self):
        return "min(%s,%s)" % (self.arg(0), \
                               self.arg(1))

class Clamp(Op):

    def __init__(self,arg,ival):
        Op.__init__(self,OpType.CLAMP,[arg])
        self._interval = ival

    @property
    def interval(self):
        return self._interval

    def compute(self,bindings):
        result = self.arg(0).compute(bindings)
        return self._interval.clamp(result)

    def __repr__(self):
        return "clamp(%s,%s)" % (self.arg(0), \
                              self._interval)

class Abs(Op):

    def __init__(self,arg):
        Op.__init__(self,OpType.ABS,[arg])
        pass

    @staticmethod
    def from_json(obj):
        return Abs(Op.from_json(obj['args'][0]))

    def compute(self,bindings):
        return abs(self.arg(0).compute(bindings))


    def substitute(self,args):
        return Abs(self.arg(0).substitute(args))


class Sgn(Op):

    def __init__(self,arg):
        Op.__init__(self,OpType.SGN,[arg])
        pass

    @staticmethod
    def from_json(obj):
        return Sgn(Op.from_json(obj['args'][0]))

    def substitute(self,assigns):
        return Sgn(self.arg(0).substitute(assigns))

    def compute(self,bindings):
        return math.copysign(1.0,self.arg(0).compute(bindings).real)


class Ln(Op):

    def __init__(self,arg):
        Op.__init__(self,OpType.LN,[arg])
        pass


class Exp(Op):

    def __init__(self,arg):
        Op.__init__(self,OpType.EXP,[arg])
        pass


class Sin(Op):

    def __init__(self,arg1):
        Op.__init__(self,OpType.SIN,[arg1])
        pass

    def compute(self,bindings):
        return math.sin(self.arg(0).compute(bindings).real)


    def substitute(self,args):
        return Sin(self.arg(0).substitute(args))

    @staticmethod
    def from_json(obj):
        return Sin(Op.from_json(obj['args'][0]))

class Cos(Op):

    def __init__(self,arg1):
        Op.__init__(self,OpType.COS,[arg1])
        pass

    def compute(self,bindings):
        return math.cos(self.arg(0).compute(bindings).real)


    @staticmethod
    def from_json(obj):
        return Cos(Op.from_json(obj['args'][0]))


    def substitute(self,args):
        return Cos(self.arg(0).substitute(args))



class Pow(Op):

    def __init__(self,arg1,arg2):
        Op.__init__(self,OpType.POW,[arg1,arg2])
        pass

    @property
    def arg1(self):
        return self.arg(0)
    @property
    def arg2(self):
        return self.arg(1)

    @staticmethod
    def from_json(obj):
        return Pow(Op.from_json(obj['args'][0]), \
                   Op.from_json(obj['args'][1]))



    def substitute(self,args):
        return Pow(
            self.arg(0).substitute(args),
            self.arg(1).substitute(args)
        )


    def compute(self,bindings):
        return self.arg(0).compute(bindings)**self.arg(1).compute(bindings)



def Sqrt(a):
    return Pow(a,genop.Const(0.5))

def Square(a):
    return genop.Mult(a,a)

def Div(a,b):
    return genop.Mult(a,Pow(b,genop.Const(-1)))


import sympy

class FromSympyFailed(Exception):
    pass

class SympyExtvar(sympy.Function):

    @classmethod
    def name(self):
        return "extvar"

    @classmethod
    def eval(cls, x):
        return None

    def _eval_is_real(self):
        return self.args[0].is_real

    def fdiff(self, argindex=1):
        if argindex == 1:
            return 1.0
        else:
            raise ArgumentIndexError(self, argindex)


class SympyEmit(sympy.Function):


    @classmethod
    def name(self):
        return "emit"


    @classmethod
    def eval(cls, x):
        return None

    def _eval_is_real(self):
        return self.args[0].is_real

    def fdiff(self, argindex=1):
        if argindex == 1:
            return 1.0
        else:
            raise ArgumentIndexError(self, argindex)

def to_sympy(expr,symbols={},wildcard=False,blacklist={},no_aliasing=False):
    assert(not (no_aliasing and wildcard))
    if expr.op == OpType.VAR:
        if wildcard:
            if not expr.name in symbols:
                bl = blacklist[expr.name] if expr.name in blacklist \
                        else []
                symbols[expr.name] = [sympy.Wild(expr.name, \
                                                    exclude=bl)]
        else:
            if not expr.name in symbols:
                symbols[expr.name] = []

            if no_aliasing:
                name = "%s.%d" % (expr.name,len(symbols[expr.name]))
                symbols[expr.name].append(sympy.Symbol(name))

            elif len(symbols[expr.name]) == 0:
                symbols[expr.name].append(sympy.Symbol(expr.name))

        return symbols[expr.name][-1]

    elif expr.op == OpType.CONST:
        if (expr.value).is_integer():
            return int(expr.value)
        else:
            return expr.value

    elif expr.op == OpType.ADD:
        args0 = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
        args1 = to_sympy(expr.args[1],symbols,wildcard,blacklist,no_aliasing)
        return args0+args1

    elif expr.op == OpType.MULT:
        args0 = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
        args1 = to_sympy(expr.args[1],symbols,wildcard,blacklist,no_aliasing)
        return args0*args1

    elif expr.op == OpType.EMIT:
        args0 = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
        return sympy.Function("emit")(args0)

    elif expr.op == OpType.EXTVAR:
        args0 = to_sympy(genop.Var(expr.name),symbols,wildcard,blacklist,no_aliasing)
        return sympy.Function("extvar")(args0)

    elif expr.op == OpType.INTEG:
        args0 = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
        args1 = to_sympy(expr.args[1],symbols,wildcard,blacklist,no_aliasing)
        return sympy.Function("integ")(args0, \
                                    args1)

    elif expr.op == OpType.POW:
        args0 = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
        args1 = to_sympy(expr.args[1],symbols,wildcard,blacklist,no_aliasing)
        if isinstance(args1,int) and args1 > 1:
            for _ in range(args1-1):
                args = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
                args0 *= args
            return args0
        else:
            return sympy.Pow(args0,args1)

    elif expr.op == OpType.MAX:
        args0 = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
        args1 = to_sympy(expr.args[1],symbols,wildcard,blacklist,no_aliasing)
        return sympy.Function("max")(args0,args1)


    elif expr.op == OpType.ABS:
        args0 = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
        return sympy.Function("abs")(args0)


    elif expr.op == OpType.SGN:
        args0 = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
        return sympy.Function("sgn")(args0)


    elif expr.op == OpType.SIN:
        args0 = to_sympy(expr.args[0],symbols,wildcard,blacklist,no_aliasing)
        return sympy.sin(args0)

    elif expr.op == OpType.FUNC:
        args = list(map(lambda v: to_sympy(genop.Var(v), \
                                           symbols, \
                                           wildcard, \
                                           blacklist,no_aliasing), \
                        expr.func_args))
        body = to_sympy(expr.expr,symbols,wildcard,blacklist,no_aliasing)
        args.append(body)
        return sympy.Function("func")(*args)

    elif expr.op == OpType.CALL:
        symargs = list(map(lambda v: to_sympy(v,symbols,wildcard,blacklist,no_aliasing),
                           expr.values))
        symbody = to_sympy(expr.func,symbols,wildcard,blacklist,no_aliasing)
        args = [symbody]+symargs
        fxn = sympy.Function("call")(*args)
        return fxn
    else:
        raise Exception("unimpl: %s" % expr)

def from_sympy(symexpr,no_aliasing=False):
    if isinstance(symexpr,sympy.Function):
        if isinstance(symexpr, sympy.sin):
            e0 = from_sympy(symexpr.args[0],no_aliasing)
            return Sin(e0)

        elif symexpr.func.name == "integ":
            assert(len(symexpr.args) == 2)
            e1 = from_sympy(symexpr.args[0],no_aliasing)
            e2 = from_sympy(symexpr.args[1],no_aliasing)
            return genop.Integ(e1,e2)


        elif symexpr.func.name == "max":
            assert(len(symexpr.args) == 2)
            e1 = from_sympy(symexpr.args[0],no_aliasing)
            e2 = from_sympy(symexpr.args[1],no_aliasing)
            return Max(e1,e2)

        elif symexpr.func.name == "abs":
            e1 = from_sympy(symexpr.args[-1],no_aliasing)
            return Abs(e1)

        elif symexpr.func.name == "sgn":
            e1 = from_sympy(symexpr.args[-1],no_aliasing)
            return Sgn(e1)

        elif symexpr.func.name == "call":
            efn = from_sympy(symexpr.args[0],no_aliasing)
            args = list(map(lambda e : from_sympy(e,no_aliasing), \
                            symexpr.args[1:]))
            return genop.Call(args,efn)

        elif symexpr.func.name == "func":
            ebody = from_sympy(symexpr.args[-1],no_aliasing)
            pars = list(map(lambda e: from_sympy(e,no_aliasing).name, \
                            symexpr.args[:-1]))
            return Func(pars,ebody)

        elif symexpr.func.name == "extvar":
            e1 = from_sympy(symexpr.args[-1],no_aliasing)
            assert(isinstance(e1,genop.Var))
            return genop.ExtVar(e1.name)


        elif symexpr.func.name == "emit":
            e1 = from_sympy(symexpr.args[-1],no_aliasing)
            return genop.Emit(e1)

        elif symexpr.func.name == "map":
            raise FromSympyFailed("cannot convert mapping %s back to expr" % symexpr)

        else:
            raise Exception("unhandled func: %s" % (symexpr.func))

    elif isinstance(symexpr, sympy.Pow):
        e1 = from_sympy(symexpr.args[0],no_aliasing)
        e2 = from_sympy(symexpr.args[1],no_aliasing)
        return Pow(e1,e2)

    elif isinstance(symexpr, sympy.Symbol):
        if no_aliasing:
            name = symexpr.name.split(".")[0]
        else:
            name = symexpr.name

        return genop.Var(name)

    elif isinstance(symexpr, sympy.Float) or \
         isinstance(symexpr, sympy.Integer):
        return genop.Const(float(symexpr))

    elif isinstance(symexpr, sympy.Mul):
        args = list(map(lambda a: from_sympy(a,no_aliasing), \
                        symexpr.args))
        return genop.product(args)
    elif isinstance(symexpr, sympy.Add):
        args = list(map(lambda a: from_sympy(a,no_aliasing), \
                        symexpr.args))
        return genop.sum(args)
    elif isinstance(symexpr, sympy.Rational):
        return genop.Const(float(symexpr))
    else:
        print(symexpr.func)
        raise Exception(sympy.srepr(symexpr))

def equivalent(expr1,expr2):
    e1_syms,e2_syms = {},{}
    se1 = to_sympy(expr1,e1_syms)
    se2 = to_sympy(expr2,e2_syms)
    is_equal = se1 - se2 == 0
    return is_equal

def simplify(expr):
    e_syms = {}
    se = to_sympy(expr,e_syms)
    se_simpl = sympy.simplify(se)
    return from_sympy(se_simpl)
