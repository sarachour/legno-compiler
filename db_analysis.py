from scipy.optimize import curve_fit
import numpy as np
import hwlib.physdb as physdb
import hwlib.hcdc.hcdcv2 as hcdclib
import hwlib.adp as adplib
import hwlib.block as blocklib
import matplotlib.pyplot as plt

dev = hcdclib.get_device()
db = physdb.PhysicalDatabase('board6')

xcat = "pmos" #this can change
ycat = "nmos" #this can change 
zcat = "cost" #this should not be changed

data_list_of_dicts = []

counter = 0

where_clause = {}
for row in db.select(where_clause):
	cfg = physdb.PhysCfgBlock.from_json(db,dev,row)
	#print(cfg.model.delta_model)
	#print(cfg.model.params)
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
	counter+=1

#this is specific to the data being plotted, will need to be changed if xcat,ycat change
isolate_rows = []
for row in data_list_of_dicts:
	if (row["gain_cal"] == row["bias_in0"]) and \
	(row["gain_cal"] == row["bias_in1"]) and \
	(row["gain_cal"] == row["bias_out"]):
		isolate_rows.append(row)





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


data_to_plot = np.zeros((8,8))
for datapoint in data_to_assemble:
	xcoord = datapoint[0]
	ycoord = datapoint[1]
	zcoord = datapoint[2]
	data_to_plot[xcoord][ycoord] = zcoord

#print(data_to_plot)
plt.imshow(data_to_plot, cmap='hot', interpolation='nearest')
plt.gca().invert_yaxis()
plt.xlabel(xcat)
plt.ylabel(ycat)
plt.title(zcat)
plt.show()

# xcoord_ycoord_list is because the independent variables need to be packed into the first argument
def uncorrelated_func(xcoord_ycoord_list,a,b,c):
	return a*xcoord_ycoord_list[0]+b*xcoord_ycoord_list[1]+c

def correlated_func(xcoord_ycoord_list,a,b,c,d):
	return a*xcoord_ycoord_list[0]+b*xcoord_ycoord_list[1]+c*xcoord_ycoord_list[0]*xcoord_ycoord_list[1]+d

uncorrelated_parameters = curve_fit(uncorrelated_func, (xcat_list,ycat_list), zcat_list)
correlated_parameters = curve_fit(correlated_func, (xcat_list,ycat_list), zcat_list)
print("uncorrelated parameters are:", uncorrelated_parameters)
print("correlated parameters are:", correlated_parameters)

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