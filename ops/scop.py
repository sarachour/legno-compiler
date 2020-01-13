#TODO: refactor this
#TODO: update gpkit
from enum import Enum

class SCOpType(Enum):
    MULT  = "*"
    ADD = "+"
    CONST = "const"
    VAR = "var"

class SCOp:

    def __init__(self,op,args):
        assert(isinstance(op,SCOpType))
        self._args = args
        self._op = op


    def factor_const(self):
        raise NotImplementedError

    def arg(self,i):
        return self._args[i]

    @property
    def op(self):
        return self._op

    def __repr__(self):
        argstr = " ".join(map(lambda x : str(x),self._args))
        return "(%s %s)" % (self._op.value,argstr)

class SCVar(SCOp):

    def __init__(self,name,exponent=1.0):
        SCOp.__init__(self,SCOpType.VAR,[])
        self._name = name
        self._exponent = exponent

    @property
    def exponent(self):
        return self._exponent

    def factor_const(self):
        return 1,self

    def evaluate(self,args):
        if not self._name in args:
            for v in args.keys():
                print(v)
            raise Exception("cannot evaluate <%s> not in assignments" % self._name)
        return args[self._name]**self._exponent
    @property
    def name(self):
        return self._name

    def __repr__(self):
        if self._exponent == 1.0:
            return "(var %s)" % self._name
        else:
            return "(var %s exp=%f)" % (self._name,self._exponent)

class SCConst(SCOp):

    def __init__(self,value):
        SCOp.__init__(self,SCOpType.CONST,[])
        self._value = float(value)


    def factor_const(self):
        return self._value,SCConst(1.0)

    def evaluate(self,args):
        return self._value

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return "(const %s)" % self._value

class SCMult(SCOp):

    def __init__(self,arg1,arg2):
        SCOp.__init__(self,SCOpType.MULT,[arg1,arg2])

    def factor_const(self):
        c1,x1 = self.arg(0).factor_const()
        c2,x2 = self.arg(1).factor_const()
        c = c1*c2
        if x1.op == SCOpType.CONST and x2.op == SCOpType.CONST:
            return c, SCConst(1.0)
        elif x1.op == SCOpType.CONST:
            return c, x2
        elif x2.op == SCOpType.CONST:
            return c, x1
        else:
            return c,SCMult(x1,x2)


    def evaluate(self,args):
        return self.arg(0).evaluate(args)*self.arg(1).evaluate(args)



class SCAdd(SCOp):

    def __init__(self,arg1,arg2):
        SCOp.__init__(self,SCOpType.ADD,[arg1,arg2])

    def factor_const(self):
        return 1.0,self


    def evaluate(self,args):
        return self.arg(0).evaluate(args)+self.arg(1).evaluate(args)



def expo(jexpr, factor):
    if jexpr.op == SCOpType.CONST:
        return SCConst(jexpr.value**factor)
    elif jexpr.op == SCOpType.VAR:
        return SCVar(jexpr.name,exponent=jexpr.exponent*factor)
    elif jexpr.op == SCOpType.MULT:
        e1 = expo(jexpr.arg(0),factor)
        e2 = expo(jexpr.arg(1),factor)
        return SCMult(e1,e2)
    else:
        raise Exception("exponentiate: not-impl %s" % jexpr)

def simplify(jexpr):
    if jexpr.op == SCOpType.CONST:
        return SCConst(jexpr.value)
    elif jexpr.op == SCOpType.VAR:
        return SCVar(jexpr.name,jexpr.exponent)
    elif jexpr.op == SCOpType.MULT:
        c,e = jexpr.factor_const()
        if c == 1.0:
            return e
        else:
            return SCMult(SCConst(c),e)
