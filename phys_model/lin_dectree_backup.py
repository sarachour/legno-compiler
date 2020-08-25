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
      self.bounds[var] = (wnull(max,l,minval), \
                          wnull(min,u,minval))

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

class DecisionNode:

  def __init__(self,name,value,left,right):
    self.name = name
    self.value = value
    self.left = left
    self.right = right

  def evaluate(self,hidden_state):
    if hidden_state[self.name] < self.value:
      return self.left.evaluate(hidden_state)
    else:
      return self.right.evaluate(hidden_state)

  def pretty_print(self,indent=0):
    ind = " "*indent
    st = "%sif %s < %f:\n" % (ind,self.name,self.value)
    st += self.left.pretty_print(indent+1)
    st += "%sif %s >= %f:\n" % (ind,self.name,self.value)
    st += self.right.pretty_print(indent+1)
    return st


  def update(self,region=None):
    if region is None:
      region = Region()

    eps = 0.5
    left_region = region.copy()
    left_region.set_range(self.name,None,self.value-eps)
    self.left.update(left_region)
    right_region = region.copy()
    right_region.set_range(self.name,self.value,None)
    self.right.update(right_region)

  def from_json(self):
    raise Exception("implement me!")


  def to_json(self):
    return {
      'name':self.name,
      'value':self.value,
      'left':self.left.to_json(),
      'right':self.right.to_json()
    }

  def find_minimum(self):
    raise Exception("implement me")

class RegressionLeafNode:

  def __init__(self,expr,npts=0,R2=-1.0,params={}):
    self.expr = expr
    self.npts = npts
    self.R2 = R2
    self.params = params
    self.parent = None
    self.region = None

  def update(self,reg):
    self.region = reg

  def pretty_print(self,indent=0):
    ind = " "*indent
    return "%sexpr %s, npts=%d, R2=%f, pars=%s\n" \
      % (ind,self.expr,self.npts,self.R2,self.params)

  def evaluate(self,hidden_state):
    assigns = dict(list(self.params.items()) +
                   list(hidden_state.items()))
    return self.expr.compute(assigns)

  def from_json(self):
    raise Exception("implement me!")

  def to_json(self):
    raise Exception("implement me!")

  def find_minimum(self):
    raise Exception("implement me")

