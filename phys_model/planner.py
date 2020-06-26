import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import itertools

import phys_model.phys_util as phys_util

class ProfilePlanner:

  def __init__(self,block,loc,cfg):
    self.block = block
    self.loc = loc
    self.config = cfg

  def next_hidden(self):
    raise NotImplementedError

  def new_dynamic(self,cfg):
    raise NotImplementedError


  def next_dynamic(self):
    raise NotImplementedError


class BruteForcePlanner(ProfilePlanner):

  def __init__(self,block,loc,cfg,n,m):
    ProfilePlanner.__init__(self,block,loc,cfg)
    self.n = n					#outer dimensions of search space
    self.m = m					#resolution (linspace) of search space
    self.block = block
    self.loc = loc
    self.cfg = cfg

  def new_hidden(self):				#hidden code is a particular set of nmos,pmos, etc
    #print(self.config["nmos"].value)
    #help(self.config)
    #print(dir(self.config["nmos"]))
    #help(self.config["nmos"])
    hidden = {}
    for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), self.block.state):
      hidden[state] = phys_util.select_from_array(state.values,self.n)
      #print("hidden[state] is: ", hidden[state])
      print("state is: ",state)
    print("hidden is: ", hidden)
    self._hidden_fields = list(hidden.keys())
    print("_hidden_fields are: ", self._hidden_fields)
    hidden_values = list(map(lambda k :hidden[k], self._hidden_fields))
    print("hidden_values are: ", hidden_values)
    self.hidden_iterator = itertools.product(*hidden_values)
    self.dynamic_iterator = None        

  def next_hidden(self):
    try:
      values = next(self.hidden_iterator)
      print("values are ", values)
      return dict(zip(self._hidden_fields,values))
    except StopIteration:
      return None

  def new_dynamic(self):
    # build up dynamically changing codes
    assert(self.dynamic_iterator is None)
    variables = []
    blk = self.block
    for out in blk.outputs:
      variables += list(out.relation[self.config.mode].vars())

    dynamic = {}
    for inp in filter(lambda inp: inp.name in variables, blk.inputs):
      dynamic[inp] = phys_util.select_from_interval(inp.interval[self.config.mode],self.m)

    for data in filter(lambda dat: dat.name in variables, blk.data):
      dynamic[data] = phys_util.select_from_quantized_interval(data.interval[self.config.mode], data.quantize[self.config.mode], self.m)

    self._dynamic_fields = list(dynamic.keys())
    dynamic_values = list(map(lambda k :dynamic[k], self._dynamic_fields))
    self.dynamic_iterator = itertools.product(*dynamic_values)

  def next_dynamic(self):
    assert(not self.dynamic_iterator is None)
    try:
      values = next(self.dynamic_iterator)
      return dict(zip(self._dynamic_fields,values))
    except StopIteration:
      self.dynamic_iterator = None
      return None

class GenericHiddenCodeIterator:
  def __init__(self,output_codes):
    self.index = 0
    self.output_codes = output_codes
    #print("in generic iterator output_codes is ", output_codes)

  def __iter__(self):
    return self

  def __next__(self):
    try:
      result = self.output_codes[self.index]
      #print("in generic iterator result is ", result)
      _output_fields = list(result.keys())
      output_values = list(map(lambda k :result[k], _output_fields))
      #print("!!!generic iterator called, returning: ", result)
    except IndexError:
      raise StopIteration
    self.index += 1
    return output_values


class SensitivityPlanner(BruteForcePlanner):
  def __init(self,block,loc,cfg,n,m):
    BruteForcePlanner.__init(self,block,loc,cfg,n,m)

  def new_hidden(self):

    svd = {}
    hidden = {}
    output_codes = []

    for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), self.block.state):
      hidden[state] = phys_util.select_from_array(state.values,self.n)
      svd[state] = self.config[state.name].value

    for state in hidden:
      for experiment_val in hidden[state]:
        new_row = dict(svd)
        new_row[state] = experiment_val
        #print("new_row is", new_row, "\n\n")
        output_codes.append(new_row)
        #print("output_codes is ", output_codes,"\n\n")
        #print("experiment_val is ", experiment_val)
        #print("output_codes[-1] is ", output_codes[-1])


    output_codes = [row for row in output_codes if row != dict(svd)]
    output_codes.append(dict(svd))


    self._hidden_fields = list(hidden.keys())
    hidden_values = list(map(lambda k :hidden[k], self._hidden_fields))

    #for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), self.block.state):
    #  hidden[state] = phys_util.select_from_array(state.values,self.n)
    #  svd[state] = self.config[state.name].value
    #  for experiment_val in hidden[state]:
    #    output_codes.append(svd)
    #    #print("output_codes is ", output_codes)
    #    print("experiment_val is ", experiment_val)
    #    print("output_codes[-1] is ", output_codes[-1])
    #    output_codes[-1][state] = experiment_val





    #print("_hidden_fields are: ", self._hidden_fields)
    #print("hidden_values are: ", hidden_values)
    #print("output_codes are: ", output_codes)

    #self.hidden_iterator = itertools.product(*hidden_values)
    #self.dynamic_iterator = None        

    self.hidden_iterator = GenericHiddenCodeIterator(output_codes)
    self.dynamic_iterator = None




class NeighborhoodPlanner(BruteForcePlanner):

  def __init__(self,block,loc,cfg,n,m):
    BruteForcePlanner.__init__(self,block,loc,cfg,n,m)

  def new_hidden(self):
    hidden = {}
    for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), self.block.state):
      #print("state is: ", state)
      valid = list(map(lambda delta: self.config[state.name].value + delta, range(-self.n,self.n+1)))
      hidden[state] = list(filter(lambda val: val in valid,state.values))
      #print("hidden[state] is :", hidden[state], "\n\n\n")
    self._hidden_fields = list(hidden.keys())
    hidden_values = list(map(lambda k :hidden[k], self._hidden_fields))
    self.hidden_iterator = itertools.product(*hidden_values)
    self.dynamic_iterator = None




class CorrelationPlanner(BruteForcePlanner):
  def __init(self,block,loc,cfg,n,m):
    BruteForcePlanner.__init(self,block,loc,cfg,n,m)

  def new_hidden(self):

    svd = {}
    hidden = {}
    output_codes = []

    for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), self.block.state):
      hidden[state] = phys_util.select_from_array(state.values,self.n)
      svd[state] = self.config[state.name].value

    state_list = list(filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), self.block.state))
    correlation_pairs = []

    for element in itertools.combinations(state_list,2):
      correlation_pairs.append(element)

    for current_pair in correlation_pairs:
      for experiment_index in range(self.n):
        new_row = dict(svd)
        new_row[current_pair[0]] = hidden[current_pair[0]][experiment_index]
        new_row[current_pair[1]] = hidden[current_pair[1]][experiment_index]
        output_codes.append(new_row)

    self._hidden_fields = list(hidden.keys())
    hidden_values = list(map(lambda k :hidden[k], self._hidden_fields))  

    self.hidden_iterator = GenericHiddenCodeIterator(output_codes)
    self.dynamic_iterator = None