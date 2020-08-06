import phys_model.model_fit as fitlib

class DecisionNode:

  def __init__(self,name,value,left,right):
    self.name = name
    self.value = value
    self.left = left
    self.right = right
    self.left_bounds = {}
    self.right_bounds = {}

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
    self.left_bounds = bounds
    self.right_bounds = bounds
    lower = 0
    upper = 1
    self.left_bounds[self.name][upper] = self.value
    self.right_bounds[self.name][lower] = self.value
    return



class RegressionLeafNode:

  def __init__(self,expr,npts=0,R2=-1.0,params={}):
    self.expr = expr
    self.npts = npts
    self.R2 = R2
    self.params = params

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

