import random
import math

class Region():
  '''
  def __init__(self,bounds = None):
    self.bounds = {'pmos':[0,7],\
                   'nmos':[0,7],\
                   'gain_cal':[0,63],\
                   'bias_out':[0,63],\
                   'bias_in0':[0,63],\
                   'bias_in1':[0,63]}
    if not bounds is None:
      self.set_ranges(bounds)
  '''
  def __init__(self,bounds=None):
    self.bounds = {}
    if not bounds is None:
      self.set_ranges(bounds)

  def to_json(self):
    return self.bounds

  @staticmethod
  def from_json(obj):
    reg = Region(obj)
    return reg

  def set_range(self,var,minval,maxval):
    assert(isinstance(var,str))
    def wnull(fn,a,b):
      if a is None:
        return b
      elif b is None:
        return a
      else:
        return fn(a,b)

    if not var in self.bounds:
      self.bounds[var] = (minval,maxval)
    else:
      l,u = self.bounds[var]
      self.bounds[var] = (wnull(max,l,minval),wnull(min,u,maxval))

  def set_ranges(self,ranges):
    for k,(l,u) in ranges.items():
      self.set_range(k,l,u)

  def extend_range(self,var,minval,maxval):
    assert(isinstance(var,str))
    def wnull(fn,a,b):
      if a is None:
        return b
      elif b is None:
        return a
      else:
        return fn(a,b)


    if not var in self.bounds:
      self.bounds[var] = (minval,maxval)

    else:
      l,u = self.bounds[var]
      self.bounds[var] = (wnull(min,l,minval),wnull(max,u,maxval))



  def add_point(self,pt):
    for var,val in pt.items():
      self.extend_range(var,val,val)

  def copy(self):
    reg = Region(dict(self.bounds))
    return reg

  def combinations(self):
    combos = 1
    for l,u in self.bounds.values():
      if not l is None and not u is None:
        combos *= math.ceil(u)-math.floor(l)+1
    return combos


  def area(self):
    area = 1
    for l,u in self.bounds.values():
      if not l is None and not u is None:
        area *= max(u-l,0)
    return area

  def intersect(self,reg):
    assert(isinstance(reg,Region))
    res = Region()
    res.set_ranges(self.bounds)
    for par,(l,u) in reg.bounds.items():
      res.set_range(par,l,u)
    return res

  def __repr__(self):
    return str(self.bounds)

  def random_code(self):
    output_code = {}
    for code in self.bounds:
      #print("lower bound is:",self.bounds[code][0], " upper bound is ",self.bounds[code][1])
      lower = math.ceil(self.bounds[code][0])
      upper = math.floor(self.bounds[code][1])
      output_code[code] = random.randint(lower,upper)
      assert(self.valid_code(output_code))
    return output_code

  def valid_code(self, test_code):
    for code in test_code:
      lower = self.bounds[code][0]
      upper = self.bounds[code][1]
      assert(lower <= upper)
      if not test_code[code] <= upper or \
         not test_code[code] >= lower:
        return False

    return True

  def overlap(self,reg):
    targ_reg = Region(self.bounds)
    for var,(lower,upper) \
        in reg.bounds.items():
      targ_reg.set_range(var,lower,upper)

    if targ_reg.area() == 0:
      return None

    return targ_reg




