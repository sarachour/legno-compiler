import math
import ops.base_op as oplib

class Interval:

    def __init__(self,lb,ub):
        assert(not Interval.isnan(lb))
        assert(not Interval.isnan(ub))
        self._lower = lb
        self._upper = ub


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


    def max(self,other):
        new_lower = max(self.lower,other.lower)
        new_upper = max(self.upper,other.upper)
        return Interval.type_infer(new_lower,new_upper)

    def min(self,other):
        new_lower = min(self.lower,other.lower)
        new_upper = min(self.upper,other.upper)
        return Interval.type_infer(new_lower,new_upper)

    def sgn(self):
        if self.crosses_zero():
            return Interval.type_infer(-1,1)
        elif self.positive():
            return Interval.type_infer(1,1)
        elif self.negative():
            return Interval.type_infer(-1,-1)


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

    def reciprocal(self):
        if self.unbounded():
            return self
        if self.contains_zero():
            print(self)
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
        elif v == -1.0:
            return self.reciprocal()
        elif v > 0:
            return self.simple_power(v)
        else:
            print(v)
            raise Exception("?")

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


def propagate_intervals(expr,ivals):
    if expr.op == oplib.OpType.VAR:
        return ivals.get(expr.name)
    elif expr.op == oplib.OpType.EMIT:
        return propagate_intervals(expr.arg(0), \
                                   ivals)
    elif expr.op == oplib.OpType.MULT:
        i0 = propagate_intervals(expr.arg(0),ivals)
        i1 = propagate_intervals(expr.arg(1),ivals)
        return i0.mult(i1)

    elif expr.op == oplib.OpType.SGN:
        i0 = propagate_intervals(expr.arg(0),ivals)
        return i0.sgn()

    elif expr.op == oplib.OpType.ABS:
        i0 = propagate_intervals(expr.arg(0),ivals)
        return i0.abs()

    elif expr.op == oplib.OpType.POW:
        i0 = propagate_intervals(expr.arg(0),ivals)
        i1 = propagate_intervals(expr.arg(1),ivals)
        return i0.power(i1)

    elif expr.op == oplib.OpType.CALL:
        conc_expr = expr.concretize()
        return propagate_intervals(conc_expr,ivals)

    elif expr.op == oplib.OpType.CONST:
        return Interval(expr.value,expr.value)

    else:
        raise Exception("expression: %s" % (expr))
