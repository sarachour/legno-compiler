from enum import Enum
import ops.op as oplib

class AOpType(Enum):

    SUM = "+"
    LN = "ln"
    EXP = "exp"
    INV = "inv"
    VPROD = "*"
    CPROD = ".*"
    VAR = "v"
    PREC = "prec"
    CONST = "c"
    SQUARE = "sq"
    SQRT = "sqrt"
    INTEG = "integ"
    EMIT = "emit"
    EXTVAR = "ev"
    CALL = "call"

class AOp:

    def __init__(self,op,inps):
        for inp in inps:
            assert(isinstance(inp,AOp))

        self._inputs = inps
        self._op = op

    
    @property
    def inputs(self):
        return self._inputs

    def input(self,v):
        return self._inputs[v]

    def _xform_inputs(self,inputs,rules,n_rules):
        if len(inputs) == 0:
            yield n_rules,[]
            return

        inp = inputs[0]
        for n_left,new_inp in inp.xform(rules,n_rules):
            if len(inputs) > 1:
                for rec_n_left, rec_new_inps in \
                    self._xform_inputs(inputs[1:],
                                       rules,
                                       n_left):

                    yield rec_n_left,[new_inp]+rec_new_inps

            else:
                yield n_left,[new_inp]

    def xform(self,rules,n_rules):
        nodes = []
        for n_rules_left, new_inps in \
            self._xform_inputs(self.inputs,rules,n_rules):
            this_node = self.make(new_inps)
            if not str(this_node) in nodes:
                yield n_rules,this_node
                nodes.append(str(this_node))

            if n_rules > 0:
                for rule in rules:
                    for new_node in rule.apply(this_node):
                        if not str(new_node) in nodes:
                            yield n_rules-1,new_node
                            nodes.append(str(new_node))

    @property
    def op(self):
        return self._op

    def to_expr(self):
        raise Exception("cannot convert to op: %s" % self)

    def hash(self):
        return hash(str(self))

    def vars(self):
        vars = []
        for inp in self.inputs:
            vars += inp.vars()
        return vars

    def make(self,ctor,inputs):
        return ctor(inputs)

    def label(self):
        return self.op.value

    def tostr(self,delim='\n',indent='   ',prefix=''):
        argstr = ""
        for inp in self._inputs:
            inp.tostr(delim=delim,indent=indent,prefix=prefix+indent)
        return prefix+self.label()+delim+argstr

    def __repr__(self):
        argstr = " ".join(map(lambda x: str(x), self._inputs))
        return "(%s %s)" % (self.label(),argstr)

class AExtVar(AOp):

    def __init__(self,var,loc=None):
        AOp.__init__(self,AOpType.EXTVAR,[])
        self._var = var
        self._loc = loc

    def make(self,inputs):
        return AExtVar(self._var, self._loc)

    @property
    def loc(self):
        return self._loc

    def has_loc(self):
        return (not self._loc is None)

    @property
    def name(self):
        return self._var

    def vars(self):
        return [self._var]

    def label(self):
        return str(self._var)


class AVar(AOp):

    def __init__(self,var,coeff=1.0):
        AOp.__init__(self,AOpType.VAR,[])
        self._var = var
        self._coeff = coeff

    def make(self,inputs):
        return AVar(self._var,self._coeff)

    def is_constant(self):
        return False

    @property
    def coefficient(self):
        return self._coeff

    @property
    def name(self):
        return self._var

    def vars(self):
        return [self._var]

    def label(self):
        if self._coeff == 1.0:
            return str(self._var)
        else:
            return "%s*%f" % (self._var,self._coeff)

class AConst(AOp):

    def __init__(self,value):
        AOp.__init__(self,AOpType.CONST,[])
        self._value = value

    def to_expr(self):
        return oplib.Const(self._value)

    @property
    def value(self):
        return self._value

    def make(self,inputs):
        return AConst(self._value)

    def label(self):
        return str("%.3e" % self._value)


class AGain(AOp):

    def __init__(self,value,expr):
        AOp.__init__(self,AOpType.CPROD, [expr])
        assert(not isinstance(expr,AGain))
        assert(isinstance(expr,AOp))
        assert(isinstance(value,float) or \
               isinstance(value,int))
        self._value = value

    @property
    def value(self):
        return self._value

    @property
    def input(self):
        return self._inputs[0]

    def make(self,inputs):
        if self._value != 1.0:
            return AGain(self._value,inputs[0])
        else:
            return inputs[0]

    @property
    def value(self):
        return self._value

    def label(self):
        return self.op.value + " "+ str(self._value)

class AProd(AOp):

    def __init__(self,inputs):
        AOp.__init__(self,AOpType.VPROD,inputs)

    def make(self,inputs):
        return AProd(inputs)


    @staticmethod
    def terms(obj):
        if isinstance(obj,AProd):
            for inp in obj.inputs:
                if isinstance(inp,AProd):
                    for t in AProd.terms(inp):
                        yield t
                else:
                    yield inp

        else:
            yield obj

    def make(self,inputs):
        return AProd.make(inputs)

    @staticmethod
    def make(inputs):
        terms = []
        print(inputs)
        for inp in inputs:
            for t in AProd.terms(inp):
                terms.append(t)

        if len(terms) > 1:
            return AProd(terms)
        elif len(terms) == 1:
            return terms[0]
        else:
            raise Exception("cannot make product with 0 terms")


class ASum(AOp):

    def __init__(self,inputs):
        for inp in inputs:
            assert(not isinstance(inp,ASum))
        AOp.__init__(self,AOpType.SUM,inputs)


    @staticmethod
    def terms(obj):
        if isinstance(obj,ASum):
            for inp in obj.inputs:
                if isinstance(inp,ASum):
                    for t in ASum.terms(inp):
                        yield t
                else:
                    yield inp

        else:
            yield obj

    def make(self,inputs):
        return ASum.make(inputs)

    @staticmethod
    def make(inputs):
        terms = []
        for inp in inputs:
            for t in ASum.terms(inp):
                terms.append(t)

        return ASum(terms)


class APrec(AOp):

    def __init__(self,expr):
        AOp.__init__(self,AOpType.PREC,[expr])

    def make(self,inputs):
        return APrec(inputs[0])


    def to_expr(self):
        return oplib.Paren(self.input(0).to_expr())

class AInteg(AOp):

    def __init__(self,expr,ic):
        AOp.__init__(self,AOpType.INTEG,[expr,ic])

    def make(self,inputs):
        return AInteg(inputs[0],inputs[1])


class AFunc(AOp):

    def __init__(self,kind,inputs,expr=None, loc=None):
        AOp.__init__(self,kind,inputs)
        self._expr = expr
        self._loc = loc

    def make(self,inputs):
        return AFunc(self._op,inputs,self._expr,self._loc)


    @property
    def has_loc(self):
        return not self._loc is None

    @property
    def loc(self):
        return self._loc


    @property
    def expr(self):
        return self._expr


    def __repr__(self):
        argstr = " ".join(map(lambda x: str(x), self._inputs))
        funstr = str(self._expr)
        return "(%s %s {%s})" % (self.label(),argstr,funstr)


