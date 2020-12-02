CALIBRATING A NEW BLOCK

Generating the first decision tree (from scratch):

-To generate the structure of the first decision tree, you would want to gather a large (500-1000 hidden codes) dataset on which to place the decision nodes.
-This will be handled by build_static_tree.py and will take multiple hours to gather the required data.
-Set target_block.py to the location of the new block you want to calibrate
-In build_static_tree.py, set the variable named "output" (around line 100) to the variable you want to fit a decision tree to (param_D, cost, param_A)
-Also give the .json filename on line 117 something unique and relevant to the data you are collecting eg "static_dectree_param_D.json"
-Run build_static_tree.py, this will gather the data (slow) and fit the first decision tree

Reparameterizing the decision tree with new data:

-reparameterize_dectree,py will handle this part, it will open the dectree named on line 38 and save a new one named on line 133
-it will use a temp db named on line 38, make sure this is empty or a new unique name before you run the script, so you are fitting
to only the minimum amount of data
-the variable of interest (param_D, param_A, cost) is set on line 99, this needs to match with that from before otherwise your results
will be weird
-run reparameterize_dectree.py to gather the minimum amount of data to reparameterize the dectree, and also perform the reparameterization

Minimizing functions of trees
-once the dectrees of interest have been created and parameterized by the above methods, it is possible to use lin_dectree_algebra.py to combine them,
and subsequently find the minimum of functions of dectrees.
-on line 32 is the input string for the expression of interest
-running lin_dectree_algebra.py should demonstrate the generation of a tree from a combination of decision trees
-this could be minimised and the result fed back into a SinglePointPlanner to profile, and then evaluate how accurate the prediction generated was
