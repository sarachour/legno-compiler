from scipy.optimize import curve_fit
from scipy.interpolate import griddata
import numpy as np
import hwlib.physdb as physdb
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.adp as adplib
import hwlib.block as blocklib
import matplotlib.pyplot as plt
import math
import itertools

dev = hcdclib.get_device()
db = physdb.PhysicalDatabase('board6')

xcat = "pmos" #this can change
ycat = "nmos" #this can change 
zcat = "param_A" #this should be either "cost", "param_A", "param_D"

data_list_of_dicts = []

counter = 0

where_clause = {}
for row in db.select(where_clause):
	cfg = physdb.PhysCfgBlock.from_json(db,dev,row)
	#print(cfg.model.delta_model)
	#print(cfg.model.params["a"])
	#input("press enter to continue")
	blk = cfg.block
	data_list_of_dicts.append({})
	for state in filter(lambda st: isinstance(st.impl, \
                          blocklib.BCCalibImpl), \
                        blk.state):
		name = cfg.cfg[state.name].name
		value = cfg.cfg[state.name].value
		data_list_of_dicts[counter][name] = value
	data_list_of_dicts[counter]["cost"] = cfg.model.cost
	data_list_of_dicts[counter]["param_A"] = cfg.model.params["a"]
	data_list_of_dicts[counter]["param_D"] = cfg.model.params["d"]
	counter+=1

isolate_rows = []

acceptable_short_values = [0,1,2,4,5,6,7]
acceptable_long_values = [0,4,8,12,20,24,28]

for row in data_list_of_dicts:
	if ((row[xcat] in acceptable_short_values) or (row[xcat] in acceptable_long_values))\
	and ((row[ycat] in acceptable_short_values) or (row[ycat] in acceptable_long_values))\
	or ((row["pmos"] == 3) and (row["nmos"] == 3) and (row["gain_cal"] == 16)\
	and (row["bias_out"] == 16) and (row["bias_in1"] == 16) and (row["bias_in0"] == 16)):
		isolate_rows.append(row)

#this is specific to the data being compared, will need to be changed if xcat,ycat change

'''
#FOR COMPARING PMOS, NMOS

for row in data_list_of_dicts:
	if (row["gain_cal"] == row["bias_in0"]) and \
	(row["gain_cal"] == row["bias_in1"]) and \
	(row["gain_cal"] == row["bias_out"]):
		isolate_rows.append(row)
'''

'''
#FOR COMPARING NMOS, BIAS_IN0
for row in data_list_of_dicts:
	if (row["gain_cal"] == row["bias_in1"]) and \
	(row["gain_cal"] == row["bias_out"]) and \
	(row["pmos"] == 3):
		isolate_rows.append(row)

'''

'''
#FOR COMPARING BIAS_IN0, BIAS_IN1
for row in data_list_of_dicts:
	if (row["gain_cal"] == row["bias_out"]) and \
	(row["nmos"] == row["pmos"]) and \
	(row["nmos"] == 3) and (row["gain_cal"] == 16):
		isolate_rows.append(row)
'''
'''
for row in data_list_of_dicts:
	if (row["gain_cal"] == row["bias_in1"]) and \
	(row["gain_cal"] == row["bias_in0"]) and \
	(row["nmos"] == 3):
		isolate_rows.append(row)
'''

#print(isolate_rows)

xcat_list = []
ycat_list = []
zcat_list = []
for row in isolate_rows:
	xcat_list.append(row[xcat])
	ycat_list.append(row[ycat])
	zcat_list.append(row[zcat])


data_to_assemble = []
for i in range(len(zcat_list)):
	data_to_assemble.append([xcat_list[i],ycat_list[i],zcat_list[i]])




'''
THIS IS A HACK - to make an 8x8 heatmap matplotlib.imshow wants an array which is constructed using 0->7 coords but the actual
axes vary from 0->28 if you are plotting bias_something or gain_cal, so you need to divide by 4 to assemble the array
'''

data_to_plot = np.zeros((max(ycat_list)+1,max(xcat_list)+1))
data_to_plot[:] = np.NaN

#print(data_to_plot)
data_to_assemble = np.array(data_to_assemble)
for datapoint in data_to_assemble:					
	xcoord_in_array = math.floor(datapoint[0])					# if xcat is pmos, nmos
	#xcoord_in_array = math.floor(datapoint[0]/4)	# if xcat is bias_XXX or gain_cal 
	ycoord_in_array = math.floor(datapoint[1])					# if ycat is pmos, nmos
	#ycoord_in_array = math.floor(datapoint[1]/4)	# if ycat is bias_XXX or gain_cal 
	zcoord = datapoint[2]
	#print(ycoord_in_array)
	#print(xcoord_in_array)
	data_to_plot[ycoord_in_array,xcoord_in_array] = zcoord

#x_axis_list = sorted(set(xcat_list))
#y_axis_list = sorted(set(ycat_list))
x_axis_list = np.arange(min(xcat_list),max(xcat_list))
y_axis_list = np.arange(min(ycat_list),max(ycat_list)+1)


fi, ax = plt.subplots()
im = ax.imshow(data_to_plot)

ax.set_xticks(np.arange(len(x_axis_list)))
ax.set_yticks(np.arange(len(y_axis_list)))
ax.set_xticklabels(x_axis_list)
ax.set_yticklabels(y_axis_list)

ax.set_title(zcat)


#INTERPOLATE
points_to_interpolate = []
for coordinate in itertools.product(x_axis_list,y_axis_list):
	points_to_interpolate.append(coordinate)


grid_x, grid_y = np.mgrid[0:len(x_axis_list),0:len(y_axis_list)]


data_to_plot2 = griddata(data_to_assemble[:,:2], data_to_assemble[:,2], (grid_x, grid_y), method="cubic")


constructed_data = np.zeros((len(y_axis_list),len(x_axis_list)))
for x in range(len(data_to_plot2)):
	for y in range(len(data_to_plot2[0])):
		constructed_data[y,x] = data_to_plot2[x,y]


im = plt.imshow(constructed_data, cmap='hot', interpolation='nearest')
#im = plt.imshow(data_to_plot, cmap='hot', interpolation='nearest')
plt.gca().invert_yaxis()		#THIS MIGHT BE CAUSING PROBLEMS
plt.xlabel(xcat)
plt.ylabel(ycat)
cbar = ax.figure.colorbar(im, ax=ax)
cbar.ax.set_ylabel("value",rotation=-90,va="bottom")

#plt.show()
plt.savefig("figures/all/0320/"+ zcat +"/0320_" + xcat + "_" + ycat + "_" + zcat + ".png")

#CURVE FITTING FOLLOWS FROM HERE

# xcoord_ycoord_list is because the independent variables need to be packed into the first argument
def uncorrelated_func(xcoord_ycoord_list,a,b,c):
	return a*xcoord_ycoord_list[0]+b*xcoord_ycoord_list[1]+c

def correlated_func(xcoord_ycoord_list,a,b,c,d):
	return a*xcoord_ycoord_list[0]+b*xcoord_ycoord_list[1]+c*xcoord_ycoord_list[0]*xcoord_ycoord_list[1]+d

uncorrelated_parameters = curve_fit(uncorrelated_func, (xcat_list,ycat_list), zcat_list)
correlated_parameters = curve_fit(correlated_func, (xcat_list,ycat_list), zcat_list)

#print("uncorrelated parameters are:", uncorrelated_parameters)
#print("correlated parameters are:", correlated_parameters)


#THIS IS THE OLD CODE TO RETRIEVE DATA FROM THE DB
'''

conn = sqlite3.connect("board6.db")

print("Opened database successfully")
cursor = conn.cursor()
cursor.execute('SELECT hidden_config, dataset, cost FROM physical')

rows = cursor.fetchall()
hidden_config_data_cost = []

for row in rows:
	hidden_config_data_cost.append(row)
 
conn.close()
print(json.load(hidden_config_data_cost[0][0]))
print(type(physdb.decode_dict(hidden_config_data_cost[0][1])))
print("Completed successfully")
'''