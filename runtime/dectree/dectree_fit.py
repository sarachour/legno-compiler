from random import seed
from random import randrange
from csv import reader
from sklearn.linear_model import LinearRegression
import ops.opparse as opparse
import runtime.dectree.region as regionlib
import runtime.dectree.dectree as dectreelib

import numpy as np
import warnings

def gini_score(inputs,output):
  reg = LinearRegression().fit(inputs, output)
  if len(output) >= 2:
    R2_score = reg.score(inputs, output)
  else:
    R2_score = 0.0
  return R2_score

# Calculate the Gini index for a split dataset
def gini_index(input_groups,output_groups):
  def n_samples(group):
    return len(group)
  # count all samples at split point
  total_points = float(sum([n_samples(group) for group in input_groups]))
  n_groups = len(input_groups)
  # sum weighted Gini index for each group
  gini = 0.0
  for group_index in range(n_groups):
    input_group = input_groups[group_index]
    output_group = output_groups[group_index]
    size = float(n_samples(input_group))
    # avoid divide by zero
    if size == 0:
      continue

    score = gini_score(input_group,output_group)
    gini += (1.0-score) * (size / total_points)

  return gini


# Create a terminal node value
def to_terminal(inputs,output):
  reg = LinearRegression().fit(inputs, output)
  R2_score = reg.score(inputs, output)
  return {
    "model":reg,
    "R2":R2_score,
    "npts":len(inputs)
  }


# Create child splits for a node or make terminal
def split(node, max_depth, min_size, depth):
    input_left, input_right = node['input_groups']
    output_left, output_right = node['output_groups']
    del (node['input_groups'])
    del (node['output_groups'])
    # check for a no split
    if not input_left:
      assert(input_right)
      node['left'] = node['right'] = to_terminal(input_right, \
                                                 output_right)
      return

    # check for a no split
    if not input_right:
      assert(input_left)
      node['left'] = node['right'] = to_terminal(input_left, \
                                                 output_left)
      return

    # check for max depth
    if depth >= max_depth:
      node['left'] = to_terminal(input_left,output_left)
      node['right'] = to_terminal(input_right,output_right)
      return

    # process left child
    if len(input_left) <= min_size:
        node['left'] = to_terminal(input_left,output_left)
    else:
        node['left'] = get_split(input_left,output_left)
        split(node['left'], max_depth, min_size, depth + 1)

    # process right child
    if len(input_right) <= min_size:
        node['right'] = to_terminal(input_right,output_right)
    else:
        node['right'] = get_split(input_right,output_right)
        split(node['right'], max_depth, min_size, depth + 1)


# Split a dataset based on an attribute and an attribute value
def test_split(input_index, input_value, inputs, output):
    left_indices, right_indices = list(), list()
    for idx, inp in enumerate(inputs):
        if inp[input_index] < input_value:
            left_indices.append(idx)
        else:
            right_indices.append(idx)

    left_inputs = list(map(lambda idx: inputs[idx], left_indices))
    left_output = list(map(lambda idx: output[idx], left_indices))
    right_inputs = list(map(lambda idx: inputs[idx], right_indices))
    right_output = list(map(lambda idx: output[idx], right_indices))
    return (left_inputs,right_inputs), (left_output,right_output)


# Select the best split point for a dataset
def get_split(inputs, output):
    n_rows = len(inputs)
    n_inputs = len(inputs[0])
    b_index, b_value, b_score = 999, 999, 999
    b_input_groups,b_output_groups = None, None
    for index in range(n_inputs):
        for row in inputs:
            input_groups,output_groups = test_split(index, \
                                                    row[index], \
                                                    inputs, \
                                                    output)
            gini = gini_index(input_groups,output_groups)
            if gini < b_score:
                b_index, b_value, b_score = index, row[index], gini
                b_input_groups = input_groups
                b_output_groups = output_groups

    return {'index':b_index, \
            'value':b_value, \
            'input_groups':b_input_groups, \
            'output_groups':b_output_groups}


# Build a decision tree
def build_tree(inputs, output, max_depth, min_size):
    root = get_split(inputs, output)
    split(root, max_depth, min_size, 1)
    return root


# Make a prediction with a decision tree
def predict(node, row):
    if row[node['index']] < node['value']:
        if isinstance(node['left'], dict):
            return predict(node['left'], row)
        else:
            return node['left'].predict([row])[0]
    else:
        if isinstance(node['right'], dict):
            return predict(node['right'], row)
        else:
            return node['right'].predict([row])[0]

def finalize_tree(input_names,node):
  if not 'left' in node and not 'right' in node:
    indices = list(range(len(node['model'].coef_)))
    assert(len(input_names) >= len(indices))
    terms = list(map(lambda idx: "c%d*%s" % (idx+1,input_names[idx]), indices))
    terms.append("c0")
    expr_str = "+".join(terms)
    expr = opparse.parse_expr(expr_str)

    params = {"c0":node['model'].intercept_}
    for idx,coeff in enumerate(node['model'].coef_):
      params["c%d" % (idx+1)] = coeff

    return dectreelib.RegressionLeafNode(expr,\
                              npts=node['npts'], \
                              R2=node['R2'], \
                              params=params)
  else:
    left = finalize_tree(input_names,node['left'])
    right = finalize_tree(input_names,node['right'])
    return dectreelib.DecisionNode(input_names[node['index']], \
                        node['value'], \
                        left, right)


# Classification and Regression Tree Algorithm
def fit_decision_tree(input_names,inputs, output, bounds, max_depth, min_size):
    if max_depth == 0:
      tree = to_terminal(inputs,output)
    else:
      tree = build_tree(inputs, output, max_depth, min_size)

    clstree = finalize_tree(input_names,tree)
    clstree.update(regionlib.Region(bounds))
    predictions = list()
    for idx in range(len(inputs)):
      predictions.append(clstree.evaluate(dict(zip(input_names,inputs[idx]))))
    return clstree,predictions


def model_error(predictions,outputs):
    model_error = 0
    n = 0
    for pred,meas in zip(predictions,outputs):
      model_error += pow(pred-meas,2)
      n += 1

    return np.sqrt(model_error/n)

