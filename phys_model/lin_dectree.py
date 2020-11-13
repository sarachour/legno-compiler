import phys_model.model_fit as fitlib
import copy
import ops.lambda_op as lambdalib
import ops.generic_op as genoplib
import phys_model.region as reglib
import ops.base_op as baselib
import json

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

  def min_sample(self):
    return self.left.min_sample() + self.left.min_sample()

  def random_sample(self,samples=[]):
    results = []
    results += self.left.random_sample(samples)
    results += self.right.random_sample(samples)
    return results


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

  def fit(self,dataset,output = []):
    hidden_codes = ['pmos', 'nmos', 'gain_cal', 'bias_in0', 'bias_in1', 'bias_out'] 

    self.left.fit(dataset)
    self.right.fit(dataset)

  def find_minimum(self):
    #reg = self.region.copy()
    #reg.set_ranges(bounds)
    #self.update(reg)
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

class RegressionLeafNode:

  def __init__(self,expr,npts=0,R2=-1.0,params={}):
    self.expr = expr
    self.npts = npts
    self.R2 = R2
    self.params = params
    self.region = reglib.Region()

  def pretty_print(self,indent=0):
    ind = "| "*indent
    return "%sexpr %s, npts=%d, R2=%f, pars=%s\n" \
      % (ind,self.expr,self.npts,self.R2,self.params)

  def min_sample(self):
    return len(self.params) + 1

  def random_sample(self,samples):
    result = []
    # count number of already valid samples
    n_valid_samples = len(list(filter(lambda samp: self.region.valid_code(samp), \
                                    samples)))

    if n_valid_samples >= self.min_sample():
      return result

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
    region = reglib.Region.from_json(dictionary['region'])
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
  def fit(self,dataset,output = []):
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
      self.params = {}
      return

    new_fit = fitlib.fit_model(self.params, self.expr, valid_dataset)
    self.params = new_fit['params']
    print("FIT %d" % (npts_valid))

  def evaluate(self,hidden_state):
    assigns = dict(list(self.params.items()) +
                   list(hidden_state.items()))
    return self.expr.compute(assigns)

  def find_minimum(self):
    #concretize
    sub_dict = {}
    for key,value in self.params.items():
      sub_dict[key] = genoplib.Const(value)
    concrete_expr = self.expr.substitute(sub_dict)


    hidden_vars = concrete_expr.vars()
    optimal_codes = fitlib.minimize_model(hidden_vars,  \
                                          concrete_expr, {}, \
                                          self.region.bounds)
    return optimal_codes['objective_val'], optimal_codes['values']

  def update(self, reg):
    self.region = reg

  #remove
  def apply_expr_op(self,target_function, optional_arg = None):
    expr = target_function(self.expr,optional_arg)
    return RegressionLeafNode(expr,self.npts,self.R2,self.params,self.region)
    

  def concretize(self):
    new_params = {}
    sub_dict = {}
    for key,value in self.params.items():
      sub_dict[key] = genoplib.Const(value)
    new_expr = self.expr.substitute(sub_dict)
    return RegressionLeafNode(new_expr,self.npts,self.R2,new_params,self.region)

  def copy(self):
    return RegressionLeafNode(self.expr,self.npts,self.R2,self.params,self.region)
