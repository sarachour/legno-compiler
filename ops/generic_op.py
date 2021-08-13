from ops.base_op import *
import ops.interval as interval

class Integ(GenericOp2):

    def __init__(self,deriv,init_cond):
        GenericOp.__init__(self,OpType.INTEG,[deriv,init_cond])
        pass

    def substitute(self,bindings={}):
        inp = self.arg(0).substitute(bindings)
        ic = self.arg(1).substitute(bindings)
        return Integ(inp,ic)

    @property
    def handle(self):
        return self._handle

    @property
    def deriv(self):
        return self.arg1

    @property
    def init_cond(self):
        return self.arg2

    @staticmethod
    def from_json(obj):
        return Integ(Op.from_json(obj['args'][0]), \
                     Op.from_json(obj['args'][1]))

    def pretty_print(self):
        return "integ(%s,%s)" % (self.deriv.pretty_print(), \
                                 self.init_cond.pretty_print())



class ExtVar(GenericOp):

    def __init__(self,name,loc=None):
        GenericOp.__init__(self,OpType.EXTVAR,[])
        assert(isinstance(name,str))
        self._name = name
        self._loc = loc

    @property
    def loc(self):
        return self._loc

    @property
    def name(self):
        return self._name

    @property
    def name(self):
        return self._name

    def compute(self,bindings={}):
      return bindings[self._name]

    def __repr__(self):
      return "(%s %s)" % \
        (self._op.value,self._name)

    def vars(self):
        return [self._name]


    @staticmethod
    def from_json(obj):
      return ExtVar(obj['name'],obj['physical'])


    def to_json(self):
      obj = Op.to_json(self)
      obj['name'] = self._name
      obj['physical'] = self._physical
      return obj

    def pretty_print(self):
        return "extvar(%s)" % (self.args[0].pretty_print())


class Var(Op):

    def __init__(self,name,latex_style=None):
        GenericOp.__init__(self,OpType.VAR,[])
        self._name = name
        self._latex_style = latex_style

    def to_json(self):
        obj = Op.to_json(self)
        obj['name'] = self._name
        return obj

    def concretize(self):
        return Var(self._name,latex_style=self._latex_style)

    def __repr__(self):
        return "(%s %s)" % \
            (self._op.value,self._name)

    @staticmethod
    def from_json(obj):
        return Var(obj['name'])

    @property
    def name(self):
        return self._name

    def substitute(self,assigns):
        if not self._name in assigns:
            return self
        else:
            return assigns[self._name]

    def compute(self,bindings={}):
        if not self._name in bindings:
            for key in bindings:
                print(key)
            raise Exception("<%s> not bound" % self._name)

        return bindings[self._name]

    def vars(self):
        return [self._name]

    def pretty_print(self):
        fmtstr = "%s"
        if not self._latex_style is None:
            fmtstr = self._latex_style % fmtstr

        return fmtstr % self.name




class Const(GenericOp):
    STRING_PRECISION = 2
    STRING_SIGFIGS = 1

    def __init__(self,value,tag=None,latex_style=None):
        GenericOp.__init__(self,OpType.CONST,[])
        self._value = float(value)
        self._latex_style = latex_style

    def to_json(self):
        obj = Op.to_json(self)
        obj['value'] = self._value
        return obj

    def substitute(self,bindings={}):
        return Const(self._value, \
                     latex_style=self._latex_style)

    def concretize(self):
        return Const(self._value,  \
                     latex_style=self._latex_style)

    @staticmethod
    def from_json(obj):
        return Const(obj['value'])

    def compute(self,bindings={}):
        return self._value

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return "(%s %s)" % \
            (self._op.value,self._value)


    def pretty_print(self):
        thresh = 1.0/(10**(Const.STRING_PRECISION - Const.STRING_SIGFIGS+1))
        if abs(self.value) < thresh  and abs(self.value) > 0.0:
            fmtstr = "%."+str(Const.STRING_PRECISION)+"e"
        elif self.value.is_integer():
            fmtstr = "%d"
        else:
            fmtstr = "%."+str(Const.STRING_PRECISION)+"f"

        if not self._latex_style is None:
            fmtstr = self._latex_style % fmtstr

        if self.value < 0:
            fmtstr = "(%s)" % fmtstr
            return fmtstr % self.value
        else:
            return fmtstr % self.value


class Emit(Op):

    def __init__(self,node,loc=None):
        Op.__init__(self,OpType.EMIT,[node])
        self._loc = loc
        pass

    def substitute(self,bindings={}):
        inp = self.arg(0).substitute(bindings)
        return Emit(inp,self._loc)


    @property
    def loc(self):
        return self._loc

    def compute(self,bindings={}):
        return self.arg(0).compute(bindings)


    def pretty_print(self):
        return "emit(%s)" % (self.args[0].pretty_print())




class Paren(Op):

    def __init__(self,arg):
        Op.__init__(self,OpType.PAREN,[arg])
        pass

    @staticmethod
    def from_json(obj):
        return Paren(Op.from_json(obj['args'][0]))

    def compute(self,bindings={}):
        return self.arg(0).compute(bindings)


    def substitute(self,args):
        return Paren(self.arg(0).substitute(args))

    def pretty_print(self):
        return "(%s)" % (self.args[0].pretty_print())






class Mult(GenericOp2):

    def __init__(self,arg1,arg2):
        GenericOp2.__init__(self,OpType.MULT,[arg1,arg2])
        pass


    @staticmethod
    def from_json(obj):
        return Mult(Op.from_json(obj['args'][0]),
                    Op.from_json(obj['args'][1]))

    def substitute(self,assigns):
        return Mult(self.arg1.substitute(assigns),
                    self.arg2.substitute(assigns))


    def infer_interval(self,intervals):
        is1 = self.arg1.infer_interval(intervals)
        is2 = self.arg2.infer_interval(intervals)
        return is1.merge(is2,
                  is1.interval.mult(is2.interval))

    def compute_op2(self,arg1,arg2):
        return arg1*arg2

    def pretty_print(self):
        coeff,base_expr = factor_coefficient(self.args[1])
        return "(%s*%s)" % (self.args[0].pretty_print(), \
                          self.args[1].pretty_print())



class Add(GenericOp2):

    def __init__(self,arg1,arg2):
        GenericOp2.__init__(self,OpType.ADD,[arg1,arg2])
        pass

    @staticmethod
    def from_json(obj):
        return Add(Op.from_json(obj['args'][0]), \
                   Op.from_json(obj['args'][1]))



    def substitute(self,args):
        return Add(
            self.arg(0).substitute(args),
            self.arg(1).substitute(args)
        )



    def compute_op2(self,arg1,arg2):
        return arg1+arg2

    def pretty_print(self):
        return "(%s)+(%s)" % (self.args[0].pretty_print(), \
                              self.args[1].pretty_print())



class Call(GenericOp):
    def __init__(self, params, expr):
        self._func = expr
        self._params = params
        GenericOp.__init__(self,OpType.CALL,params+[self._func])
        assert(expr.op == OpType.FUNC)

    def compute(self,bindings={}):
        new_bindings = {}
        for func_arg,var in zip(self._func.func_args,self._params):
            expr = var.compute(bindings)
            new_bindings[func_arg] = expr

        value = self._func.compute(new_bindings)
        return value

    @property
    def func(self):
        return self._func

    @property
    def values(self):
        return self._params

    def concretize(self):
        expr = self._func.apply(self._params)
        return expr


    def substitute(self,args):
        pars = list(map(lambda val: val.substitute(args), \
                        self.values))
        fxn = self.func.substitute(args)
        return Call(pars,fxn)


    def to_json(self):
        obj = Op.to_json(self)
        pars = []
        for par in self._params:
            pars.append(par.to_json())
        obj['expr'] = self._expr.to_json()
        obj['values'] = pars
        return obj


    def __repr__(self):
        pars = " ".join(map(lambda p: str(p), self._params))
        return "call(%s, %s)" % (pars,self._func)

def product(terms):
    if len(terms) == 0:
        return Const(1)
    elif len(terms) == 1:
        return terms[0]
    else:
        return Mult(terms[0],product(terms[1:]))


def sum(terms):
    if len(terms) == 0:
        return Const(0)
    elif len(terms) == 1:
        return terms[0]
    else:
        return Add(terms[0],sum(terms[1:]))

def factor_positive_coefficient(expr):
    coeff,base_expr = factor_coefficient(expr)
    if coeff > 0:
        return coeff,base_expr
    else:
        return abs(coeff),Mult(Const(-1.0),base_expr)

def unpack_sum(expr):
    if expr.op == OpType.CONST:
        return expr.value,[]
    elif expr.op == OpType.VAR:
        return 0.0,[expr]
    elif expr.op == OpType.ADD:
        c1,vs1 = unpack_sum(expr.arg(0))
        c2,vs2 = unpack_sum(expr.arg(1))
        return c1+c2,vs1+vs2
    elif expr.op == OpType.MULT:
        coeff,vs = unpack_product(expr)
        if len(vs) == 1:
            c1,vs1 = unpack_sum(vs[0])
            vs_upd = list(map(lambda v: Mult(Const(coeff), v), vs1))
            return coeff*c1, vs_upd

        else:
            return 0.0,[expr]

    else:
        return 0.0,[expr]

def _propagate_error(expr,values,coeff=False):
    if expr.op == OpType.CONST:
        return False,abs(expr.value)
    elif expr.op == OpType.VAR:
        return True,abs(values[expr.name])
    elif expr.op == OpType.POW:
        has_var1,e1 = _propagate_error(expr.arg(0),values,coeff=False)
        has_var2,e2 = _propagate_error(expr.arg(1),values,coeff=True)
        return has_var1 or has_var2, e1**e2

    elif expr.op == OpType.ABS:
        return _propagate_error(expr.arg(0),values)

    elif expr.op == OpType.MULT:
        has_var1,e1 = _propagate_error(expr.arg(0),values,coeff=True)
        has_var2,e2 = _propagate_error(expr.arg(1),values,coeff=True)
        return has_var1 or has_var2,e1*e2
    elif expr.op == OpType.ADD:
        has_var1,e1 = _propagate_error(expr.arg(0),values,coeff=True)
        has_var2,e2 = _propagate_error(expr.arg(1),values,coeff=True)
        res = 0.0
        if has_var1:
            res+=e1
        if has_var2:
            res+=2
        return has_var1 or has_var2, res
    else:
        raise Exception("unsupported: %s" % expr)

def propagate_error(expr,values):
    _,res = _propagate_error(expr,values)
    return res

def unpack_linear_operator(expr):
    offset,exprs = unpack_sum(expr)
    if(len(exprs) == 1):
        coeff,exprs = unpack_product(exprs[0])
        return coeff,offset,exprs
    elif offset == 0.0:
        coeff,exprs = unpack_product(exprs[0])
        return coeff,0.0,exprs
    else:
        return 1.0,offset,exprs


def unpack_product(expr):
    if expr.op == OpType.CONST:
        return expr.value,[]
    elif expr.op == OpType.VAR:
        return 1.0,[expr]
    elif expr.op == OpType.MULT:
        c1,vs1 = unpack_product(expr.arg(0))
        c2,vs2 = unpack_product(expr.arg(1))
        return c1*c2,vs1+vs2
    else:
        return 1.0,[expr]

def get_var(expr):
    offset,exprs = unpack_sum(expr)
    if offset != 0.0 or len(exprs) != 1:
        return None
    term = exprs[0]
    coeff,exprs = unpack_product(term)
    if coeff != 1.0 or len(exprs) != 1:
        return None
    term = exprs[0]
    if term.op == OpType.VAR:
        return term
    else:
        return None

def is_var(expr):
    result = get_var(expr)
    return not result is None

def factor_coefficient(expr):
    if expr.op == OpType.CONST:
        return expr.value,Const(1.0)
    elif expr.op == OpType.VAR:
        return 1.0,expr
    elif expr.op == OpType.EMIT:
        c1,e1 = factor_coefficient(expr.arg(0))
        return c1,Emit(e1)
    elif expr.op == OpType.MULT:
        c1,e1 = factor_coefficient(expr.arg(0))
        c2,e2 = factor_coefficient(expr.arg(1))
        res = Mult(e1,e2)
        return c1*c2,res
    elif expr.op == OpType.INTEG:
        c1,e1 = factor_coefficient(expr.arg(0))
        c2,e2 = factor_coefficient(expr.arg(1))
        if c1 == c2:
            return c1,Integ(e1,e2)
        else:
            return 1.0,expr

    elif expr.op == OpType.CALL:
        return 1.0,expr

    elif expr.op == OpType.ADD:
        c1,e1 = factor_coefficient(expr.arg(0))
        c2,e2 = factor_coefficient(expr.arg(1))
        if c1 == c2:
            return c1,Add(e1,e2)
        else:
            return 1.0,expr

    else:
            return 1.0,expr

def unpack_integ(expr):
    coeff,exprs = unpack_product(expr)
    if len(exprs) == 1 and exprs[0].op == OpType.INTEG:
        integ_expr = exprs[0]
        return Integ( \
                      Mult(Const(coeff), integ_expr.deriv), \
                      Mult(Const(coeff), integ_expr.init_cond), \
                     )
    else:
        raise Exception("cannot unpack: %s" % expr)

def break_expr_string(expr_string,max_len=70):
    terms = expr_string.split("+")
    clauses = []
    line = terms[0]
    for term in terms[1:]:
        if len(line) + len(term) > max_len:
            clauses.append(line)
            line = "+"+term
        else:
            line += "+"+term

    clauses.append(line)
    return clauses
