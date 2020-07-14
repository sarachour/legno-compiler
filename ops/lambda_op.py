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
