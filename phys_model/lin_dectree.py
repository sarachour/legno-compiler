import phys_model.model_fit as fitlib
import copy
import ops.generic_op as genoplib

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

  '''
  this function generates a sequence of leaf nodes in the decision tree.
  use the `yield` python feature to do this
  '''
  def leaves(self):
    raise Exception("implement me!")

  '''
  This function accepts a json object that was previously returned
  by the to_json routine and builds a decision tree object from the data.
  '''
  @staticmethod
  def from_json(obj):
    raise Exception("implement me!")

  '''
  This function serializes the decision tree into a json data structure.
  '''
  def to_json(self):
    raise Exception("implement me!")


  def find_minimum(self,bounds):
    self.calculate_new_bounds(bounds)
    left_minimum,left_min_code = self.left.find_minimum(self.left_bounds)
    right_minimum,right_min_code = self.right.find_minimum(self.right_bounds)

    if left_minimum < right_minimum:
      return left_minimum, left_min_code
    else:
      return right_minimum, right_min_code

  def calculate_new_bounds(self,bounds):
    '''
    bounds in the form
      {'pmos':(0,7),\
       'nmos':(0,7),\
       'gain_cal':(0,63),\
       'bias_out':(0,63),\
       'bias_in0':(0,63),\
       'bias_in1':(0,63),\
      }
    '''
    self.left_bounds = copy.deepcopy(bounds)
    self.right_bounds = copy.deepcopy(bounds)
    lower = 0
    upper = 1
    self.left_bounds[self.name][upper] = self.value - 1
    self.right_bounds[self.name][lower] = self.value
    return



class RegressionLeafNode:

  def __init__(self,expr,npts=0,R2=-1.0,params={}):
    self.expr = expr
    self.npts = npts
    self.R2 = R2
    self.params = params

    #concretize
    self.sub_dict = {}
    for key,value in self.params.items():
      self.sub_dict[key] = genoplib.Const(value)
    self.baked_expr = self.expr.substitute(self.sub_dict)
    self.expr = self.baked_expr

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
    hidden_vars = self.expr.vars()
    optimal_codes = fitlib.minimize_model(hidden_vars, self.expr, {}, bounds)
    return optimal_codes['objective_val'], optimal_codes['values']

