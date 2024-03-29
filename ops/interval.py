import math
import ops.base_op as oplib
import numpy as np

def same_sign(v,v1):
    if v*v1 >= 0:
        return True
    else:
        return False

class Interval:

    def __init__(self,lb,ub):
        assert(not Interval.isnan(lb))
        assert(not Interval.isnan(ub))
        self._lower = lb
        self._upper = ub

    def clip(self,v):
        if v >= self._upper:
            return self._upper
        elif v <= self._lower:
            return self._lower
        else:
            return v

    def union(self,i2):
      lb = min(self.lower,i2.lower)
      ub = max(self.upper,i2.upper)
      return Interval.type_infer(lb,ub)

    def intersection(self,i2):
        upper = min(i2.upper,self.upper)
        lower = max(i2.lower,self.lower)
        if upper <= lower:
            return Interval.type_infer(0,0)
        else:
            return Interval.type_infer(lower,upper)

    @staticmethod
    def zero():
        return Interval.type_infer(0,0)

    @property
    def spread(self):
        return abs(self.upper-self.lower)

    @property
    def bound(self):
        return max(abs(self.lower),abs(self.upper))

    @property
    def middle(self):
        return (self._upper+self._lower)/2.0


    @property
    def lower(self):
        return self._lower

    @property
    def upper(self):
        return self._upper


    def unbounded(self):
        return Interval.isinf(self.lower) \
            or Interval.isinf(self.upper)

    def unbounded_lower(self):
        return Interval.isinf(self.lower)

    def unbounded_upper(self):
        return Interval.isinf(self.upper)


    @staticmethod
    def isnan(num):
        return math.isnan(num)


    @staticmethod
    def isinf(num):
        return num == float('inf') \
            or num == float('-inf') \
            or num is None

    @staticmethod
    def type_infer(lb,ub):
      if Interval.isinf(lb) \
         and Interval.isinf(ub):
        return IUnknown()

      elif Interval.isinf(ub):
        assert(not Interval.isinf(lb))
        return ILowerBound(lb)

      elif abs(lb - ub) < 1e-6:
        return IValue(lb)

      else:
        return IRange(lb,ub)

    def contains_value(self,value):
        return value <= self.upper and \
            value >= self.lower

    def above(self,other):
        return self.lower >= other.upper

    def contains(self,child):
        if child.lower >= self.lower and \
           child.upper <= self.upper:
            return True
        else:
            return False

    def is_value(self,val):
        return self.lower == val and \
            self.upper == val

    def negate(self):
        return Interval.type_infer(
            -self.upper,
            -self.lower
        )

    def scale(self,v):
        assert(v > 0)
        return Interval.type_infer(
            self.lower*v,
            self.upper*v
        )

    def nonoverlapping(self,i2):
        diff1 = abs(i2.lower - self.lower)
        diff2 = abs(i2.upper - self.upper)
        return max(diff1,diff2)


    def is_constant(self):
        return self.lower == self.upper

    def contains_zero(self):
        return self.lower <= 0 and self.upper >= 0


    def crosses_zero(self):
        return self.lower < 0 and self.upper > 0

    def negative(self):
        return self.lower < 0 and self.upper < 0

    def positive(self):
        return self.lower >= 0 and self.upper >= 0


    def ratio(self,other):
        assert(same_sign(other.lower,self.lower))
        assert(same_sign(other.upper,self.upper))
        return (self.lower/other.lower,self.upper/other.upper)

    def max(self,other):
        new_lower = max(self.lower,other.lower)
        new_upper = max(self.upper,other.upper)
        return Interval.type_infer(new_lower,new_upper)

    def min(self,other):
        new_lower = min(self.lower,other.lower)
        new_upper = min(self.upper,other.upper)
        return Interval.type_infer(new_lower,new_upper)

    def sin(self):
        return Interval.type_infer(-1,1)

    def sgn(self):
        if self.crosses_zero():
            return Interval.type_infer(-1,1)
        elif self.positive():
            return Interval.type_infer(1,1)
        elif self.negative():
            return Interval.type_infer(-1,-1)


    def by_index(self,index,n):
        vals = np.linspace(self.lower,self.upper,n)
        return vals[index]


    def abs(self):
        upper = max(abs(self.lower),abs(self.upper))
        lower = min(abs(self.lower),abs(self.upper))
        if self.crosses_zero():
            return Interval.type_infer(0,upper)
        else:
            return Interval.type_infer(lower,upper)

    def simple_power(self,v):
        assert(not self.crosses_zero())
        assert(not self.negative())
        lower = self.lower**v
        upper = self.upper**v
        return Interval.type_infer(lower,upper)

    def sqrt(self):
        return self.simple_power(0.5)

    def divide(self,other):
        return self.mult(other.reciprocal())

    def reciprocal(self):
        if self.unbounded():
            return self
        if self.contains_zero():
            corners = [1.0/self.lower, 1.0/self.upper]
            return Interval.type_infer(min(corners), float('inf'))
        else:
            corners = [1.0/self.lower, 1.0/self.upper]
            return Interval.type_infer(min(corners),max(corners))

    def power(self,_v):
        if _v.is_constant():
            v = _v.lower
        else:
            v = None

        if v == 1.0:
            return self

        elif v < 0.0:
            ival = self.reciprocal()
            return ival.power(Interval.type_infer(abs(v), abs(v)))

        elif v > 0:
            return self.simple_power(v)
        else:
            print(v)
            raise Exception("%s^(%s) : can't compute" % (self,_v))

    def exponent_value(self,value):
        if value > 0:
            return Interval.type_infer(
                self.lower**value,
                self.upper**value
            )

        elif value < 0:
            ival = self.exponent_value(-value)
            return ival.reciprocal()

        else:
            return Interval.type_infer(1.0,1.0)

    def exponent(self,ival):
        if ival.spread == 0:
            return self.exponent_value(ival.value)
        else:
            raise Exception("unimpl: %s^%s" % (self,ival))


    def add(self,i2):
         vals = [
            i2.lower+self.lower,
            i2.upper+self.lower,
            i2.lower+self.upper,
            i2.upper+self.upper
         ]
         lb = min(vals)
         ub = max(vals)
         return Interval.type_infer(lb,ub)


    def equals(self,other):
        return self.upper == other.upper and \
            self.lower == other.lower

    def mult(self,i2):
        vals = [
            i2.lower*self.lower,
            i2.upper*self.lower,
            i2.lower*self.upper,
            i2.upper*self.upper
        ]
        if i2.unbounded() or self.unbounded():
            return IUnknown()

        lb = min(vals)
        ub = max(vals)
        return Interval.type_infer(lb,ub)

    @staticmethod
    def from_json(obj):
        return Interval.type_infer(
            obj['lower'],
            obj['upper']
        )


    def to_json(self):
        return {
            'lower':self.lower,
            'upper':self.upper
        }

    def __repr__(self):
        return "[%.3e,%.3e]" % (self._lower,self._upper)

    def __iter__(self):
        yield self.lower
        yield self.upper

class IValue(Interval):

    def __init__(self,value):
        self._value = value
        Interval.__init__(self,value,value)

    @property
    def value(self):
        return self._value

    def power(self,v):
        return IValue(self.value**v)

    def __iter__(self):
      yield self.lower


    def __repr__(self):
      return "[%.3e]" % self._value

class IRange(Interval):

  def __init__(self,min_value,max_value):
    Interval.__init__(self,min_value,max_value)

class ILowerBound(Interval):

  def __init__(self,min_value):
    Interval.__init__(self,min_value,float('inf'))


class IUnknown(Interval):

  def __init__(self):
    Interval.__init__(self,float('-inf'),float('inf'))

class IntervalCollection:

  def __init__(self,ival):
    if not (isinstance(ival, Interval)):
      raise Exception("not interval: <%s>.T<%s>" % \
                      (ival,ival.__class__.__name__))
    self._ival = ival
    self._bindings = {}

  def update(self,new_ival):
    assert(isinstance(new_ival, Interval))
    self._ival = new_ival

  def bind(self,name,ival):
    assert(isinstance(ival, Interval))
    assert(not name in self._bindings)
    self._bindings[name] = ival

  def bindings(self):
    return self._bindings.items()

  def get(self,name):
      return self._bindings[name]

  @property
  def interval(self):
    return self._ival

  def copy(self):
    ic = IntervalCollection(self.interval)
    for k,v in self.bindings():
      ic.bind(k,v)
    return ic

  def merge(self,other,new_ival):
    new_ivals = self.copy()
    for k,v in other.bindings():
      new_ivals.bind(k,v)

    new_ivals.update(new_ival)
    return new_ivals

  def merge_dict(self,other_dict):
    new_ivals = self.copy()
    for k,v in other_dict.items():
        new_ivals.bind(k,v)

    return new_ivals

  def dict(self):
    return dict(self._bindings)

  def __repr__(self):
    st = "ival %s\n" % self._ival
    for bnd,ival in self._bindings.items():
      st += "  %s: %s\n" % (bnd,ival)

    return st

class BackpropFailedError(Exception):
    pass


class UnknownIntervalError(Exception):
    pass

def backpropagate_intervals(expr,ival,ivals):
    def is_conc(expr):
        return all(map(lambda v: v in ivals, expr.vars()))

    if expr.op == oplib.OpType.VAR:
        if expr.name in ivals:
            return {}

        return {expr.name:ival}

    elif expr.op == oplib.OpType.EMIT:
        return backpropagate_intervals(expr.arg(0),ival,ivals)

    elif expr.op == oplib.OpType.MULT:
        ival0 = propagate_intervals(expr.arg(0),ivals) \
                if is_conc(expr.arg(0)) else None
        ival1 = propagate_intervals(expr.arg(1),ivals) \
                if is_conc(expr.arg(1)) else None
        if ival0 is None and ival1 is None:
            raise UnknownIntervalError("cannot backprop through <%s>" % expr)

        elif ival1 is None:
            return backpropagate_intervals(expr.arg(1),ival.divide(ival0),ivals)
        elif ival0 is None:
            return backpropagate_intervals(expr.arg(0),ival.divide(ival1),ivals)
        else:
            return {}


    elif expr.op == oplib.OpType.INTEG:
        raise UnknownIntervalError("cannot backprop through <%s>" % expr)
    else:
        raise BackpropFailedError("backprop expression: %s" % (expr))

def propagate_intervals(expr,ivals):
    if expr.op == oplib.OpType.VAR:
        if not expr.name in ivals:
            raise UnknownIntervalError("unknown interval for <%s>" % expr.name)
        return ivals[expr.name]

    elif expr.op == oplib.OpType.EMIT:
        return propagate_intervals(expr.arg(0), \
                                   ivals)

    elif expr.op == oplib.OpType.ADD:
        i0 = propagate_intervals(expr.arg(0),ivals)
        i1 = propagate_intervals(expr.arg(1),ivals)
        return i0.add(i1)

    elif expr.op == oplib.OpType.MULT:
        i0 = propagate_intervals(expr.arg(0),ivals)
        i1 = propagate_intervals(expr.arg(1),ivals)
        return i0.mult(i1)

    elif expr.op == oplib.OpType.SGN:
        i0 = propagate_intervals(expr.arg(0),ivals)
        return i0.sgn()

    elif expr.op == oplib.OpType.SIN:
        i0 = propagate_intervals(expr.arg(0),ivals)
        return i0.sin()

    elif expr.op == oplib.OpType.ABS:
        i0 = propagate_intervals(expr.arg(0),ivals)
        return i0.abs()

    elif expr.op == oplib.OpType.POW:
        i0 = propagate_intervals(expr.arg(0),ivals)
        i1 = propagate_intervals(expr.arg(1),ivals)
        return i0.power(i1)

    elif expr.op == oplib.OpType.CALL:
        conc_expr = expr.concretize()
        assert(len(expr.func.vars()) == 0)
        return propagate_intervals(conc_expr,ivals)

    elif expr.op == oplib.OpType.CONST:
        return Interval(expr.value,expr.value)

    elif expr.op == oplib.OpType.INTEG:
        raise UnknownIntervalError("cannot propagate through <%s>" % expr)

    elif expr.op == oplib.OpType.MAX:
        i0 = propagate_intervals(expr.arg(0),ivals)
        i1 = propagate_intervals(expr.arg(1),ivals)
        return i0.max(i1)

    else:
        raise Exception("prop expression: %s" % (expr))


def split_interval(ival,segments):
  assert(isinstance(ival,Interval))
  spread = ival.spread/(segments)
  lb = ival.lower
  for i in range(0,segments):
    ub = lb + spread
    yield Interval(lb,ub)
    lb = ub

