import phys_model.model_fit as fitlib
import copy
import ops.generic_op as genoplib
import phys_model.region as reglib

class DecisionNode:

  def __init__(self,name,value,left,right):
    self.name = name
    self.value = value
    self.left = left
    self.right = right
    self.region = reglib.Region()


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

  def from_json(self):
    raise Exception("implement me!")

  def to_json(self):
    return {
      'name':self.name,
      'value':self.value,
      'left':self.left.to_json(),
      'right':self.right.to_json()
    }

  def find_minimum(self,bounds):
    #reg = self.region.copy()
    #reg.set_ranges(bounds)
    #self.update(reg)
    left_minimum,left_min_code = self.left.find_minimum(bounds)
    right_minimum,right_min_code = self.right.find_minimum(bounds)

    if left_minimum < right_minimum:
      return left_minimum, left_min_code
    else:
      return right_minimum, right_min_code

  '''def calculate_new_bounds(self,bounds):
    self.left_bounds = copy.deepcopy(bounds)
    self.right_bounds = copy.deepcopy(bounds)
    lower = 0
    upper = 1
    self.left_bounds[self.name][upper] = self.value - 1
    self.right_bounds[self.name][lower] = self.value
    return'''

  def update(self, region=None):
    if region is None:
      region = reglib.Region()

    eps = 0.5
    left_region = region.copy()
    left_region.set_range(self.name,None,self.value-eps)
    self.left.update(left_region)
    right_region = region.copy()
    right_region.set_range(self.name, self.value, None)
    self.right.update(right_region)

class RegressionLeafNode:

  def __init__(self,expr,npts=0,R2=-1.0,params={}):
    self.expr = expr
    self.npts = npts
    self.R2 = R2
    self.params = params
    self.bounds = {}
    self.region = reglib.Region()


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

  def find_minimum(self,bounds):
    #concretize
    sub_dict = {}
    for key,value in self.params.items():
      sub_dict[key] = genoplib.Const(value)
    self.expr = self.expr.substitute(sub_dict)


    hidden_vars = self.expr.vars()
    optimal_codes = fitlib.minimize_model(hidden_vars, self.expr, {}, self.region.bounds)
    return optimal_codes['objective_val'], optimal_codes['values']

  def update(self, reg):
    self.region = reg



