class Region():

  def __init__(self):
    self.bounds = {}

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
      self.bounds[var] = (wnull(max,l,minval),wnull(min,u,minval))

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

