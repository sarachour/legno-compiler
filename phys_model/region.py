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

  def copy(self):
    reg = Region(dict(self.bounds))
    return reg

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
    raise Exception("too specialized")
    bounds = {'pmos':[0,7],\
                   'nmos':[0,7],\
                   'gain_cal':[0,63],\
                   'bias_out':[0,63],\
                   'bias_in0':[0,63],\
                   'bias_in1':[0,63]}
    is_valid_range = True
    for var in self.bounds:
      lower_A = self.bounds[var][0]
      upper_A = self.bounds[var][1]
      lower_B = reg.bounds[var][0]
      upper_B = reg.bounds[var][1]
      #print("lower_A:", lower_A)
      #print("upper_A:", upper_A)
      #print("lower_A:", lower_A)
      #print("upper_B:", upper_B)
      if lower_A > lower_B:
        target_lower = lower_A
      else:
        target_lower = lower_B

      if upper_A < upper_B:
        target_upper = upper_A
      else:
        target_upper = upper_B

      if target_upper < target_lower:
        is_valid_range = False

      bounds[var] = [target_lower,target_upper]

    return Region(bounds)




