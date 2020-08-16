import phys_model.model_fit as fitlib
import copy
import ops.generic_op as genoplib
import phys_model.region as reglib
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
  def leaves(self, flat_list = []):
    self.left.leaves(flat_list)
    self.right.leaves(flat_list)
    return flat_list

  def min_sample(self):
    return self.left.min_sample() + self.left.min_sample()

  def random_sample(self, sample_list = []):
    self.left.random_sample(sample_list)
    self.right.random_sample(sample_list)
    return sample_list


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
    value = parent['value']
    name = parent['name']
    child_nodes_dicts = [parent['left'],parent['right']]
    child_nodes = []
    for node in child_nodes_dicts:
      if node['type'] == 'DecisionNode':
        child_nodes.append(DecisionNode.from_json(node))
      elif node['type'] == 'RegressionLeafNode':
        child_nodes.append(RegressionLeafNode.from_json(node))
    return(DecisionNode(name,value,child_nodes[0],child_nodes[1]))
    '''
    '''
    if left_dict['type'] == 'DecisionNode':
      left = DecisionNode.from_json(left_dict)
    elif left_dict['type'] == 'RegressionLeafNode':
      left = RegressionLeafNode.from_json(left_dict)

    if right_dict['type'] == 'DecisionNode':
      right = DecisionNode.from_json(right_dict)
    elif right_dict['type'] == 'RegressionLeafNode':
      right = RegressionLeafNode.from_json(right_dict)
    '''

    '''
    left_dict = dictionary['left']
    right_dict = dictionary['right']
    left_obj = None
    right_obj = None
    for side in [[left_dict,left_obj],[right_dict,right_obj]]:
      if side[0]['type'] == 'DecisionNode':
        side[1] = DecisionNode.from_json(side[0])
      elif side[0]['type'] == 'RegressionLeafNode':
        side[1] = RegressionLeafNode.from_json(side[0])
    return(DecisionNode(name,value,left_obj,right_obj))
    '''
    '''
    child_nodes = []
    child_nodes_dicts = [parent['left'],parent['right']]
    for child_node in child_nodes_dicts:
      print("child_node: ", child_node)
      if child_node['type'] == 'DecisionNode':
        print("appending DecisionNode")
        child_nodes.append(DecisionNode.from_json(child_node))
      elif child_node['type'] == 'RegressionLeafNode:':
        print("appending RegressionLeafNode")
        child_nodes.append(RegressionLeafNode.from_json(child_node))
    print("child_nodes: ", child_nodes)
    return(DecisionNode(name,value,child_nodes[0],child_nodes[1]))

    '''
    
    
  



  '''
  This function serializes the decision tree into a json data structure.
  '''
  def to_json(self, dictionary):
    dictionary['type'] = "DecisionNode"
    dictionary['value'] = self.value
    dictionary['name'] = self.name
    dictionary['left'] = self.left.to_json({})
    dictionary['right'] = self.right.to_json({})

    return dictionary

  def fit(self,inputs,output):
    raise Exception("implement me!")

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

  def __init__(self,expr,npts=0,R2=-1.0,params={},region = reglib.Region()):
    self.expr = expr
    self.npts = npts
    self.R2 = R2
    self.params = params
    self.region = region


  def pretty_print(self,indent=0):
    ind = " "*indent
    return "%sexpr %s, npts=%d, R2=%f, pars=%s\n" \
      % (ind,self.expr,self.npts,self.R2,self.params)

  def min_sample(self):
    return len(self.params)

  def random_sample(self, sample_list):
    for i in range(self.min_sample()):
      sample_list.append(self.region.random_code())


  '''
  this function generates a sequence of leaf nodes in the decision tree.
  use the `yield` python feature to do this
  '''
  def leaves(self, flat_list):
    flat_list.append(self)
    return

  '''
  This function accepts a json object that was previously returned
  by the to_json routine and builds a decision tree object from the data.
  '''
  @staticmethod
  def from_json(dictionary):
    expr = dictionary['expr']
    npts = dictionary['npts']
    R2 = dictionary['R2']
    params = dictionary['params']
    region = dictionary['region']
    return RegressionLeafNode(expr,npts,R2,params,region)

  '''
  This function serializes the decision tree into a json data structure.
  '''
  def to_json(self,dictionary):
    dictionary['type'] = "RegressionLeafNode"
    dictionary['expr'] = self.expr
    dictionary['npts'] = self.npts
    dictionary['R2'] = self.R2
    dictionary['params'] = self.params
    dictionary['region'] = self.region
    
    return dictionary

  '''
  This function accepts a dictionary of input values for each hidden code
  and a list of output values. It finds the parameters for
  all the leaf nodes in the decision tree and updates the params dictionary
  and R2 value of each leaf node. The format of the inputs and output fields
  is up to you
  '''
  def fit(self,inputs,output):
    raise Exception("implement me!")

  def evaluate(self,hidden_state):
    assigns = dict(list(self.params.items()) +
                   list(hidden_state.items()))
    return self.expr.compute(assigns)

  def find_minimum(self,bounds):
    #concretize
    sub_dict = {}
    for key,value in self.params.items():
      sub_dict[key] = genoplib.Const(value)
    self.expr = self.expr.substitute(sub_dict)


    hidden_vars = self.expr.vars()
    optimal_codes = fitlib.minimize_model(hidden_vars,  \
                                          self.expr, {}, \
                                          self.region.bounds)
    return optimal_codes['objective_val'], optimal_codes['values']

  def update(self, reg):
    self.region = reg



