from enum import Enum
import itertools

class OpType(Enum):

  # generic ops that map to analog components
  MULT= "*"
  INTEG= "int"
  ADD= "+"
  CONST= "const"
  VAR= "var"
  EMIT= "emit"
  EXTVAR= "extvar"
  PAREN = "paren"
  CALL = "call"

  # special ops that can appear in functions
  FUNC = "func"
  POW= "pow"
  SGN = "sgn"
  ABS = "abs"
  COS = "cos"
  SIN = "sin"
  LN= "ln"
  EXP= "exp"
  CLAMP="clamp"
  MIN ="min"
  MAX ="max"
  ROUND ="round"

class Op:

    def __init__(self,op,args):
        for arg in args:
            if not (isinstance(arg,Op)):
                raise Exception("not op: %s" % arg)
        self._args = args
        self._op = op
        self._is_associative = True \
                               if op in [OpType.MULT, OpType.ADD] \
                                  else False


    @property
    def op(self):
        return self._op

    def arg(self,idx):
        return self._args[idx]

    @property
    def args(self):
        return self._args

    def nodes(self):
        child_nodes = [self]
        for nodes in map(lambda a: a.nodes(), self._args):
          child_nodes += nodes

        return child_nodes

    def count(self):
        child_nodes = sum(map(lambda a: a.count(), self._args))
        return 1 + child_nodes

    def depth(self):
        if len(self._args) == 0:
            return 0

        child_depth = max(map(lambda a: a.depth(), self._args))
        return 1 + child_depth

    def concretize(self):
        return self

    def __repr__(self):
        argstr = " ".join(map(lambda arg: str(arg),self._args))
        return "(%s %s)" % (self._op.value,argstr)

    def __eq__(self,other):
        assert(isinstance(other,Op))
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def bwvars(self):
        return self.vars()

    def vars(self):
        vars = []
        for arg in self._args:
            vars += arg.vars()

        return list(set(vars))

    def to_json(self):
      args = list(map(lambda arg: arg.to_json(), \
                      self._args))
      return {
        'op': self.op.value,
        'args': args
      }

    @staticmethod
    def from_json(obj):
        import ops.generic_op as generic
        import ops.lambda_op as lambd

        op = OpType(obj['op'])
        if op == OpType.VAR:
            return generic.Var.from_json(obj)
        elif op == OpType.INTEG:
            return generic.Integ.from_json(obj)
        elif op == OpType.CONST:
            return generic.Const.from_json(obj)
        elif op == OpType.FUNC:
            return generic.Func.from_json(obj)
        elif op == OpType.MULT:
            return generic.Mult.from_json(obj)
        elif op == OpType.ADD:
            return generic.Add.from_json(obj)
        elif op == OpType.POW:
            return lambd.Pow.from_json(obj)
        elif op == OpType.SGN:
            return lambd.Sgn.from_json(obj)
        elif op == OpType.ABS:
            return lambd.Abs.from_json(obj)
        elif op == OpType.SIN:
            return lambd.Sin.from_json(obj)
        elif op == OpType.COS:
            return lambd.Cos.from_json(obj)
        elif op == OpType.ROUND:
            return lambd.Round.from_json(obj)
        elif op == OpType.MAX:
            return lambd.Max.from_json(obj)
        elif op == OpType.MIN:
            return lambd.Min.from_json(obj)
        else:
            raise Exception("unimpl: %s" % obj)


    def is_constant(self):
      return False

    def copy(self):
      return Op.from_json(self.to_json())


    def substitute(self,bindings={}):
      raise Exception("substitute not implemented: %s" % self)

    def compute(self,bindings={}):
      raise Exception("compute not implemented: %s" % self)

    def is_constant(self):
        if len(self._args) == 0:
            raise Exception("unimpl: is_constant for %s" % self)
        else:
            return all(map(lambda i: i.is_constant(), \
                           self._args))



class GenericOp(Op):


    def __init__(self,op,args):
        Op.__init__(self,op,args)

    # infer bandwidth from interval information
    def infer_interval(self,interval,bound_intervals):
        raise NotImplementedError("unknown infer-interval <%s>" % (str(self)))


    # infer bandwidth from interval information
    def infer_bandwidth(self,intervals,bandwidths={}):
        raise NotImplementedError("unknown infer-bandwidth <%s>" % (str(self)))



class GenericOp2(GenericOp):

    def __init__(self,op,args):
        GenericOp.__init__(self,op,args)
        assert(len(args) == 2)

    @property
    def arg1(self):
        return self._args[0]

    @property
    def arg2(self):
        return self._args[1]

    def compute(self,bindings={}):
        arg1 = self._args[0].compute(bindings)
        arg2 = self._args[1].compute(bindings)
        return self.compute_op2(arg1,arg2)

    def compute_op2(self,arg1,arg2):
        raise Exception("compute_op2 not implemented: %s" % self)


