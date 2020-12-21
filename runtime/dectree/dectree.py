import runtime.fit.model_fit as expr_fit_lib
import copy
import ops.lambda_op as lambdalib
import ops.generic_op as genoplib
import runtime.dectree.region as regionlib
import ops.base_op as baselib
import ops.generic_op as genoplib
import json

class RegressionNodeCollection:

  def __init__(self,nodes):
    self.nodes = nodes

  def random_sample(self,samples=[]):
    new_samples = []
    for node in self.nodes:
      samps = node.random_sample(samples+new_samples)
      new_samples += samps

    return new_samples

  def fit(self,dataset):
    for node in self.nodes:
      if not node.fit(dataset):
        return False
    return True

  def vars(self):
    all_vars = []
    assert(len(self.nodes) == 1)
    for node in self.nodes:
      all_vars += node.expr.vars()
    return set(all_vars)

  def update_expr(self,lambd):
    for node in self.nodes:
      node.update_expr(lambd)

  def evaluate(self,values):
    result = None
    for node in self.nodes:
      if node.region.valid_code(values):
        assert(result is None)
        result = node.evaluate(values)

    return result

  def is_concrete(self):
    return any(map(lambda n: not n.is_concrete(), \
                   self.nodes))

  def find_minimum(self):
    minval = None
    codes = None
    for node in self.nodes:
      node_min,codes = node.find_minimum()
      if minval is None or \
         node_min < minval:
        minval = node_min
        mincodes = codes

    return minval,codes

  def __repr__(self):
    st = ""
    for node in self.nodes:
      st += str(node) + "\n"
    return st

class Node:

  def __init__(self):
    pass

  '''
  This function accepts a json object that was previously returned
  by the to_json routine and builds a decision tree object from the data.
  '''
  @staticmethod
  def from_json(parent):
    if parent['type'] == 'DecisionNode':
      name = parent['name']
      value = parent['value']
      left = DecisionNode.from_json(parent['left'])
      right = DecisionNode.from_json(parent['right'])
      return DecisionNode(name,value,left,right)
    else:
      return RegressionLeafNode.from_json(parent)

class DecisionNode(Node):

  def __init__(self,name,value,left,right):
    Node.__init__(self)
    self.name = name
    self.value = value
    self.left = left
    self.right = right

  def copy(self):
    return DecisionNode(self.name, self.value, \
                       self.left.copy(), \
                       self.right.copy())
  def evaluate(self,hidden_state):
    if hidden_state[self.name] < self.value:
      return self.left.evaluate(hidden_state)
    else:
      return self.right.evaluate(hidden_state)

  def pretty_print(self,indent=0):
    ind = "| "*indent
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
    return self.left.leaves() + self.right.leaves()

  def enough_data(self,d):
    return self.left.enough_data(d) and self.right.enough_data(d)

  def min_sample(self):
    return self.left.min_sample() + self.left.min_sample()

  def random_sample(self,samples=[]):
    r1 = self.left.random_sample(samples)
    r2 = self.right.random_sample(samples+r1)
    return r1+r2


 

  '''
  This function serializes the decision tree into a json data structure.
  '''
  def to_json(self):
    dictionary = {}
    dictionary['type'] = "DecisionNode"
    dictionary['value'] = self.value
    dictionary['name'] = self.name
    dictionary['left'] = self.left.to_json()
    dictionary['right'] = self.right.to_json()
    return dictionary

  def update_expr(self,lambd):
    self.left.update_expr(lambd)
    self.right.update_expr(lambd)

  def fit(self,dataset):
    succ = self.left.fit(dataset)
    succ &= self.right.fit(dataset)
    return succ

  def find_minimum(self):
    left_minimum,left_min_code = self.left.find_minimum()
    right_minimum,right_min_code = self.right.find_minimum()

    if left_minimum < right_minimum:
      return left_minimum, left_min_code
    else:
      return right_minimum, right_min_code

  def update(self, region):
    eps = 0.5
    left_region = region.copy()
    left_region.set_range(self.name,None,self.value-eps)
    self.left.update(left_region)
    right_region = region.copy()
    right_region.set_range(self.name, self.value, None)
    self.right.update(right_region)

  def apply_expr_op(self,target_function,optional_arg = None):
    new_left = self.left.apply_expr_op(target_function,optional_arg)
    new_right = self.right.apply_expr_op(target_function,optional_arg)
    return DecisionNode(self.name,self.value,new_left,new_right)

  def concretize(self):
    return DecisionNode(self.name,self.value,self.left.concretize(),self.right.concretize())








class RegressionLeafNode(Node):

  def __init__(self,expr,npts=0,R2=-1.0,params={}):
    Node.__init__(self)
    self.expr = expr
    self.npts = npts
    self.R2 = R2
    self.params = params
    self.region = regionlib.Region()

  def pretty_print(self,indent=0):
    ind = "| "*indent
    return "%sexpr %s, npts=%d, R2=%f, pars=%s\n" \
      % (ind,self.expr,self.npts,self.R2,self.params)


  @property
  def free_vars(self):
    return filter(lambda v: not v in self.params, self.expr.vars())

  def is_concrete(self):
    return any(map(lambda v: v is None, self.params.values()))

  def min_sample(self):
    return len(self.params) + 1

  def enough_data(self,samples):
    n_valid_samples = len(list(filter(lambda samp:
                                      self.region.valid_code(samp), \
                                      samples)))
    return self.min_sample() <= n_valid_samples

  def random_sample(self,samples):
    # count number of already valid samples
    n_valid_samples = len(list(filter(lambda samp:
                                      self.region.valid_code(samp), \
                                      samples)))

    if n_valid_samples >= self.min_sample():
      return []

    result = []
    for i in range(self.min_sample()-n_valid_samples):
      result.append(self.region.random_code())

    return result

  '''
  this function generates a sequence of leaf nodes in the decision tree.
  use the `yield` python feature to do this
  '''
  def leaves(self):
      return [self]

  '''
  This function accepts a json object that was previously returned
  by the to_json routine and builds a decision tree object from the data.
  '''
  @staticmethod
  def from_json(dictionary):
    expr = baselib.Op.from_json(dictionary['expr'])
    npts = dictionary['npts']
    R2 = dictionary['R2']
    params = dictionary['params']
    #print("\n\n\n\nparams: ", params)
    region = regionlib.Region.from_json(dictionary['region'])
    node = RegressionLeafNode(expr,npts,R2,params)
    node.region = region
    return node

  '''
  This function serializes the decision tree into a json data structure.
  '''
  def to_json(self):
    dictionary = {}
    dictionary['type'] = "RegressionLeafNode"
    dictionary['expr'] = self.expr.to_json()
    dictionary['npts'] = self.npts
    dictionary['R2'] = self.R2
    dictionary['params'] = self.params
    dictionary['region'] = self.region.to_json()
    return dictionary

  '''
  This function accepts a dictionary of input values for each hidden code
  and a list of output values. It finds the parameters for
  all the leaf nodes in the decision tree and updates the params dictionary
  and R2 value of each leaf node. The format of the inputs and output fields
  is up to you
  '''
  def fit(self,dataset):
    valid_dataset = {}
    hidden_codes = dataset['inputs'].keys()
    valid_dataset['inputs'] = dict(map(lambda k : (k,[]), dataset['inputs'].keys()))
    valid_dataset['meas_mean'] = []
    npts = len(dataset['meas_mean'])
    for idx in range(npts):
      datapoint = dict(map(lambda h: (h,dataset['inputs'][h][idx]), hidden_codes))
      if self.region.valid_code(datapoint):
        valid_dataset['meas_mean'].append(dataset['meas_mean'][idx])
        for hidden_code in hidden_codes:
          valid_dataset['inputs'][hidden_code].append(datapoint[hidden_code])


    npts_valid = len(valid_dataset['meas_mean'])
    if not npts_valid >= self.min_sample():
      print("not enough datapoints: have %d/%d points"  \
                      % (npts_valid,self.min_sample()))
      self.params = dict(map(lambda p: (p,None), \
                             self.params.keys()))
      return False

    new_fit = expr_fit_lib.fit_model(self.params, self.expr, valid_dataset)
    self.params = new_fit['params']
    return True

  def evaluate(self,hidden_state):
    assigns = dict(list(self.params.items()) +
                   list(hidden_state.items()))
    return self.expr.compute(assigns)

  def find_minimum(self):
    #concretize
    sub_dict = {}
    for key,value in self.params.items():
      if value is None:
        raise Exception("undefined variable <%s> (%s)"  \
                        % (key,self.params))
      sub_dict[key] = genoplib.Const(value)

    optimal_codes = expr_fit_lib.global_minimize_model(list(self.free_vars),  \
                                                       self.expr,  \
                                                       sub_dict, \
                                                       self.region.bounds)
    return optimal_codes['objective_val'], optimal_codes['values']

  def update(self, reg):
    self.region = reg

  def update_expr(self,lambd):
    self.expr = lambd(self.expr)

  #remove
  def apply_expr_op(self,target_function, optional_arg = None):
    expr = target_function(self.expr,optional_arg)
    return RegressionLeafNode(expr,self.npts,self.R2,self.params,self.region)


  def concretize(self):
    new_params = {}
    sub_dict = {}
    for key,value in self.params.items():
      if value is None:
         continue
      sub_dict[key] = genoplib.Const(value)

    new_expr = self.expr.substitute(sub_dict)
    leaf = RegressionLeafNode(new_expr,self.npts,self.R2,new_params)
    leaf.region = self.region.copy()
    return leaf

  def copy(self):
    node = RegressionLeafNode(self.expr,
                              npts=self.npts, \
                              R2=self.R2, \
                              params=self.params)
    node.region = self.region.copy()
    return node

  def __repr__(self):
    st = "vars=%s params=%s region=%s R2=%f\n" % (self.expr.vars(), \
                                                self.params, \
                                                self.region, \
                                                self.R2)
    st += "   %s" % self.expr
    return st

def make_constant(value):
  return RegressionLeafNode(genoplib.Const(value))
