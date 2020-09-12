import json
import phys_model.lin_dectree as lin_dectree
import ops.generic_op as genoplib
import ops.lambda_op as lambdalib
import ops.opparse as parselib
import phys_model.dectree_algebra as algebra

default_boundaries = {'pmos':[0,7],\
		            'nmos':[0,7],\
		            'gain_cal':[0,63],\
		            'bias_out':[0,63],\
		            'bias_in0':[0,63],\
		            'bias_in1':[0,63]}\

boundaries_to_ignore = dict(default_boundaries)

with open("static_dectree_param_A.json") as fh:
  serialized_dectree_dict_A = json.load(fh)
dectree_A = lin_dectree.DecisionNode.from_json(serialized_dectree_dict_A)

with open("static_dectree_cost.json") as fh:
  serialized_dectree_dict_B = json.load(fh)
dectree_B = lin_dectree.DecisionNode.from_json(serialized_dectree_dict_B)

A = dectree_A.concretize().leaves()		
B = dectree_B.concretize().leaves()
variable_bindings = {"A": A, "B": B}

#and so on for the variables you want to combine

#place the expression here
expr = parselib.parse_expr("(A^-1)*B")
leaf_list = algebra.eval_expr(expr, variable_bindings) 

tree = algebra.reconstruct(leaf_list,boundaries_to_ignore,default_boundaries)

print(tree.pretty_print())


