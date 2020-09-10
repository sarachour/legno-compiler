import json
import phys_model.lin_dectree as lin_dectree
import ops.generic_op as genoplib
import ops.lambda_op as lambdalib
import copy

def reconstruct(leaf_node_list,boundaries_to_ignore,default_boundaries):

	#if you have reached the end of a branch
	#print("\n\n\nNEW DECISION NODE CONSTRUCTOR CALLED")
	#print("argument len:",len(leaf_node_list))

	#for leaf in leaf_node_list:
	#	print("leaf.region.bounds: ", leaf.region.bounds)

	#print("ignore: ", boundaries_to_ignore)

	if len(leaf_node_list) <= 1:
		#print("REACHED END OF BRANCH, RETURNING LEAF")
		#print(leaf_node_list[0].region.bounds)
		return leaf_node_list[0]

	#otherwise continue


	boundary_freq = {'pmos':{},\
	                'nmos':{},\
	                'gain_cal':{},\
	                'bias_out':{},\
	                'bias_in0':{},\
	                'bias_in1':{}}

	#this bit is nastily hardcoded atm
	#initialise the boundary_freq_list to fill the entire range with zeroes
	for var in boundary_freq:
		for i in range(default_boundaries[var][0], 2*default_boundaries[var][1]):
			boundary_freq[var][i*0.5] = 0

	#include upper bound
	for var in boundary_freq:
		boundary_freq[var][float(boundaries_to_ignore[var][1])] = 0
	#boundary_freq initialised now

	#this actually performs the count, constructing boundary_freq
	for leaf in leaf_node_list:
		for var in leaf.region.bounds:
			boundary_freq[var][float(leaf.region.bounds[var][0])]+=1
			boundary_freq[var][float(leaf.region.bounds[var][1])]+=1

	#as janky as it is, boundaries ending in .5 are upper bounds, and so their tally should be added on to the fully rounded integer that is above them
	#the following adds all .5 tallies to the integer above

	for var in boundary_freq:
		for boundary in boundary_freq[var]:
			if not boundary % 1 == 0:
				boundary_freq[var][boundary+0.5] += boundary_freq[var][boundary]
				boundary_freq[var][boundary] = 0

	#boundaries which exist in the boundaries_to_ignore dict are trivial and will have a large amount of hits, so they need to be set to 0

	for var in boundary_freq:
		for boundary in boundaries_to_ignore[var]:
			boundary_freq[var][boundary] = 0
			#print("boundary: ", boundary, "var: ", var)

	#for readability, compress out the values that are 0

	compressed_boundary_freq =  {'pmos':{},\
	                'nmos':{},\
	                'gain_cal':{},\
	                'bias_out':{},\
	                'bias_in0':{},\
	                'bias_in1':{}}

	for var in boundary_freq:
		for boundary in boundary_freq[var]:
			if boundary_freq[var][boundary] != 0:
				compressed_boundary_freq[var][boundary] = boundary_freq[var][boundary]

	max_freq = 0
	max_loc = 0.0
	max_var = ""
	for var in boundary_freq:
		max_boundary_loc = max(boundary_freq[var].keys(), key=(lambda key: boundary_freq[var][key]))
		max_boundary_val = boundary_freq[var][max_boundary_loc]
		#print("in ",var ,"at boundary: ",max_boundary_loc," there is a value of: ", max_boundary_val)
		if max_boundary_val > max_freq:
			max_freq = max_boundary_val
			max_loc = max_boundary_loc
			max_var = var


	#print(compressed_boundary_freq)

	#print("The boundary should be at:", max_loc, " in: ", max_var, ", as ", max_freq, " leaves satisfy it")

	#time to make the first decision node


	#left leaves are below the val, right leaves are above
	#find all the leaves which have a upper bound less than or equal to 
	#val-0.5, they go in the left
	#and then find all leaves which have a lower bound greater than or equal to
	#val, and they go in the right
	left_leaves = []
	right_leaves = []

	for leaf in leaf_node_list:

		#print("leaf.region.bounds: ",leaf.region.bounds)
		#check if leaf lower bound is greater or equal to boundary 
		if leaf.region.bounds[max_var][0] >= max_loc:
			right_leaves.append(leaf)

		#check if leaf upper bound is less than or equal to boundary - 0.5
		elif leaf.region.bounds[max_var][1] <= max_loc:
			left_leaves.append(leaf)

	#print("left: ", len(left_leaves),", right: ", len(right_leaves))

	boundaries_to_ignore[max_var].append(max_loc)
	#print("boundaries to ignore:", boundaries_to_ignore)
	left_boundaries_to_ignore = copy.deepcopy(boundaries_to_ignore)
	right_boundaries_to_ignore = copy.deepcopy(boundaries_to_ignore)
	left_branch = reconstruct(left_leaves,left_boundaries_to_ignore,default_boundaries)
	right_branch = reconstruct(right_leaves,right_boundaries_to_ignore,default_boundaries)

	

	node = lin_dectree.DecisionNode(max_var,max_loc,left_branch,right_branch)

	return node


def combine(tree_A,tree_B,target_operation):

	leaf_node_list_A = tree_A.leaves() 
	leaf_node_list_B = tree_B.leaves()

	#create list of all possible new leaves

	leaf_node_list_F = []
	for leaf_A in leaf_node_list_A:
		for leaf_B in leaf_node_list_B:
			reg = leaf_A.region.overlap(leaf_B.region)
			expr = target_operation(leaf_A.expr, leaf_B.expr)
			new_leaf = lin_dectree.RegressionLeafNode(expr,region = reg)
			leaf_node_list_F.append(new_leaf)


	#remove leaves with invalid regions
	leaf_index = 0
	leaf_indices_to_remove = []
	for leaf_index in range(len(leaf_node_list_F)):
		leaf = leaf_node_list_F[leaf_index]
		for var in leaf.region.bounds:
			lower = leaf.region.bounds[var][0]
			upper = leaf.region.bounds[var][1]
			if upper < lower:
				leaf_indices_to_remove.append(leaf_index)
				break
		leaf_index+=1

	for del_index in sorted(leaf_indices_to_remove,reverse=True):	#reverse to keep indices valid after removal
		leaf_node_list_F.pop(del_index)

	default_boundaries = {'pmos':[0,7],\
		                'nmos':[0,7],\
		                'gain_cal':[0,63],\
		                'bias_out':[0,63],\
		                'bias_in0':[0,63],\
		                'bias_in1':[0,63]}


	reconstructed_tree = reconstruct(leaf_node_list_F,default_boundaries,default_boundaries)
	return reconstructed_tree


with open("static_dectree_param_A.json") as fh:
  serialized_dectree_dict_A = json.load(fh)
dectree_A = lin_dectree.DecisionNode.from_json(serialized_dectree_dict_A)

with open("static_dectree_cost.json") as fh:
  serialized_dectree_dict_B = json.load(fh)
dectree_B = lin_dectree.DecisionNode.from_json(serialized_dectree_dict_B)

A = dectree_A.concretize()
B = dectree_B.concretize()

#0.76*(A^-1)*B + B + 0.3
tree = A
tree = tree.apply_expr_op(lambdalib.Pow,genoplib.Const(-1))
tree = tree.apply_expr_op(genoplib.Mult,genoplib.Const(0.76))
tree = combine(tree,B,genoplib.Mult)
tree = combine(tree,B,genoplib.Add)
tree = tree.apply_expr_op(genoplib.Add,genoplib.Const(0.3))

print(tree.find_minimum())
print(tree.pretty_print())
#for leaf in leaf_node_list_F:
#	print(leaf.region.bounds)

#print(boundary_freq)
#boundaries dictionary is a count of 
#boundaries = {'pmos':{23:2, 25:8, 30, }}


#for leaf in leaf_node_list_F:
#	for variable in leaf.region.bounds:
#		lower = variable[0]
#		upper = variable[1]
#		boundaries[variable]

'''

#############ALGORITHM EXPLANATION###################

-define variable = dimension = one of pmos, nmos, bias_in0.....

every decision node implements a single "boundary" on a single variable, splitting it into an "above" and "below" region

for every point in the domain, a single tree specifies a single expr which is valid at that point,
the total domain being subdivided into many different valid regions (one for each leaf node)

when you combine two trees, you use a similar method to finding the cartesian product of the leaves of each tree,
where the region of each leaf is "overlapped"/"intersected"/"AND'ed" with that of the other. in the space
that satisfies both of the valid domains (the overlapping region), you can perform any of the genoplib
expression operations on the two source leaves you are working with.

to find the AND operation of the two regions, you are looking for the space where both leaves are valid. Each variable
of a leaf node will be assigned an upper and lower bound by the region property of the object. To calculate the region
in which both are valid, for each variable you must take the larger of the two lower bounds and the smaller of the two
upper bounds.

In some cases, two leaves from separate trees will not have any amount of overlap in their valid regions, this case
will present itself where the lower bound of the valid region is larger than the upper bound - this is easy to check
for, and leaves in the produced tree can simply be deleted from the combined tree. The regions of the remaining 
leaves should fully cover the entire possible input space. (maybe this is worth checking) >>>write a valid checker for this

this process will leave you with a flat list of leaves, with their relevant regions.

the next step is to reconstruct the decision tree that leaves you with these regions (i am not sure whether you want to 
include the regions you have deleted in this, as they may include important information that is required)

the input space is fully subdivided and fully covered by the valid regions (i think)

therefore the next step is to figure out how many of each leaf satisfy each possible decision node (each upper and lower
bound on any variable is a decision node)

this should give an idea of the hierarchy of decision nodes, as the boundary which the largest number of leaves satisfy will
be highest in the tree

the highest number will be at the top of the tree, after that, the data will need to be regathered as the leaves which
do and dont satisfy that condition need to be treated as entirely separate as branches cannot recombine

you need to remove the satisfied boundary from those that you consider in the child branches

so to do this you take the leaves which do satisfy the top decision node, and find the most satisfied boundary in that dataset
 -> do the same for the leaves which dont satisfy the top decision node 

the process can be completed recursively, splitting each dataset on each decision node to build up the structure of the tree
'''
