import random

class Region():
  def __init__(self):
    self.bounds = {'pmos':[0,7],\
       'nmos':[0,7],\
       'gain_cal':[0,63],\
       'bias_out':[0,63],\
       'bias_in0':[0,63],\
       'bias_in1':[0,63],\
      }

  def set_range(self,var,minval,maxval):
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
    reg = Region()
    reg.set_ranges(self.bounds)
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
      print("lower bound is:",self.bounds[code][0], " upper bound is ",self.bounds[code][1])
      output_code[code] = random.randint(self.bounds[code][0],self.bounds[code][1])
    self.valid_code(output_code)
    return output_code

  def valid_code(self, test_code):
    for code in test_code:
      if not self.bounds[code][0] <= test_code[code] <= self.bounds[code][1]:

        print("Hidden code:\n",test_code[code],"\n not in range:\n",list(range(self.bounds[code][0],self.bounds[code][1])),"\n\n")
        raise Exception('Invalid hidden code!')
    return






