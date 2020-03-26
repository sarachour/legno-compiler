from ops.base_op import *
import ops.interval as interval

class Integ(GenericOp2):

    def __init__(self,deriv,init_cond,handle):
        assert(handle.startswith(":"))

        GenericOp.__init__(self,OpType.INTEG,[deriv,init_cond])
        self._handle = handle
        pass

    def substitute(self,bindings={}):
        inp = self.arg(0).substitute(bindings)
        ic = self.arg(1).substitute(bindings)
        return Integ(inp,ic,self._handle)

    @property
    def handle(self):
        return self._handle

    @property
    def ic_handle(self):
        return self._handle+"[0]"

    @property
    def deriv_handle(self):
        return self._handle+"\'"

    @property
    def deriv(self):
        return self.arg1

    @property
    def init_cond(self):
        return self.arg2

    def coefficient(self):
        return self.deriv.coefficient()

    def handles(self):
        ch = Op.handles(self)
        assert(not self.handle in ch and \
               not self.handle is None)
        ch.append(self.handle)
        ch.append(self.ic_handle)
        ch.append(self.deriv_handle)
        return ch

    def toplevel(self):
        return self.handle

    def infer_interval(self,intervals={}):
      if not self.handle in intervals:
        raise Exception("handle not in interval: %s" % self.handle)

      ival = intervals[self.handle]
      istvar = interval.IntervalCollection(ival)
      istvar.bind(self.handle,ival)
      return istvar

    def state_vars(self):
        stvars = Op.state_vars(self)
        stvars[self._handle] = self
        return


class ExtVar(GenericOp):

    def __init__(self,name,loc=None):
        GenericOp.__init__(self,OpType.EXTVAR,[])
        self._name = name
        self._loc = loc

    def coefficient(self):
        return 1.0

    def sum_terms(self):
        return [self]

    def prod_terms(self):
        return [self]

    @property
    def loc(self):
        return self._loc

    @property
    def name(self):
        return self._name

    def infer_interval(self,bindings={}):
        return interval.IntervalCollection(bindings[self._name])

    @property
    def name(self):
        return self._name

    def compute(self,bindings={}):
      return bindings[self._name]

    def __repr__(self):
      return "(%s %s)" % \
        (self._op.value,self._name)

    @staticmethod
    def from_json(obj):
      return ExtVar(obj['name'],obj['physical'])


    def to_json(self):
      obj = Op.to_json(self)
      obj['name'] = self._name
      obj['physical'] = self._physical
      return obj

class Var(Op):

    def __init__(self,name):
        GenericOp.__init__(self,OpType.VAR,[])
        self._name = name

    def coefficient(self):
        return 1.0

    def sum_terms(self):
        return [self]

    def prod_terms(self):
        return [self]

    def to_json(self):
        obj = Op.to_json(self)
        obj['name'] = self._name
        return obj


    def __repr__(self):
        return "(%s %s)" % \
            (self._op.value,self._name)

    @staticmethod
    def from_json(obj):
        return Var(obj['name'])

    @property
    def name(self):
        return self._name

    def infer_interval(self,intervals={}):
      if not self.name in intervals:
        raise Exception("unknown interval: <%s>" % self.name)

      return interval.IntervalCollection(intervals[self._name])

    def substitute(self,assigns):
        return assigns[self._name]

    def compute(self,bindings={}):
        if not self._name in bindings:
            for key in bindings:
                print(key)
            raise Exception("<%s> not bound" % self._name)

        return bindings[self._name]


    def vars(self):
        return [self._name]



class Const(GenericOp):

    def __init__(self,value,tag=None):
        GenericOp.__init__(self,OpType.CONST,[])
        self._value = float(value)

    def to_json(self):
        obj = Op.to_json(self)
        obj['value'] = self._value
        return obj

    def substitute(self,bindings={}):
        return Const(self._value)

    @staticmethod
    def from_json(obj):
        return Const(obj['value'])


    def is_constant(self):
      return True

    def coefficient(self):
        return self.value

    def sum_terms(self):
        return [self]

    def prod_terms(self):
        return []

    def compute(self,bindings={}):
        return self._value

    def infer_interval(self,bindings):
        return interval.IntervalCollection(
            interval.IValue(self._value)
        )

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return "(%s %s)" % \
            (self._op.value,self._value)


class Emit(Op):

    def __init__(self,node,loc=None):
        Op.__init__(self,OpType.EMIT,[node])
        self._loc = loc
        pass

    @property
    def loc(self):
        return self._loc

    def compute(self,bindings={}):
        return self.arg(0).compute(bindings)

    def infer_interval(self,intervals={}):
        return self.arg(0).infer_interval(intervals)



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

    def infer_interval(self,intervals={}):
        return self.arg(0).infer_interval(intervals)





class Mult(GenericOp2):

    def __init__(self,arg1,arg2):
        GenericOp2.__init__(self,OpType.MULT,[arg1,arg2])
        pass


    @staticmethod
    def from_json(obj):
        return Mult(Op.from_json(obj['args'][0]),
                    Op.from_json(obj['args'][1]))

    def coefficient(self):
        return self.arg1.coefficient()*self.arg2.coefficient()

    def prod_terms(self):
        return self.arg1.prod_terms()+self.arg2.prod_terms()

    def sum_terms(self):
        return [self]

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


class Add(GenericOp2):

    def __init__(self,arg1,arg2):
        GenericOp2.__init__(self,OpType.ADD,[arg1,arg2])
        pass

    @staticmethod
    def from_json(obj):
        return Add(Op.from_json(obj['args'][0]), \
                   Op.from_json(obj['args'][1]))


    def coefficient(self):
        return 1.0

    def prod_terms(self):
        return [self]

    def sum_terms(self):
        return self.arg1.sum_terms() + self.arg2.sum_terms()


    def substitute(self,args):
        return Add(
            self.arg(0).substitute(args),
            self.arg(1).substitute(args)
        )


    def infer_interval(self,bindings):
        is1 = self.arg1.infer_interval(bindings)
        is2 = self.arg2.infer_interval(bindings)
        return is1.merge(is2,
                  is1.interval.add(is2.interval))



    def compute_op2(self,arg1,arg2):
        return arg1+arg2


class Call(GenericOp):
    def __init__(self, params, expr):
        self._func = expr
        self._params = params
        GenericOp.__init__(self,OpType.CALL,params+[self._func])
        assert(expr.op == OpType.FUNC)

    #def evaluate(self):
    #    self._expr = self._func.apply(self._params)

    def coefficient(self):
        return 1.0

    def prod_terms(self):
        return [self]

    def sum_terms(self):
        return [self]


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
        for v in self._params:
            yield v

    def concretize(self):
        return self._expr

    def infer_interval(self,ivals):
        return self.concretize().infer_interval(ivals)

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
        return "call %s %s" % (pars,self._func)
