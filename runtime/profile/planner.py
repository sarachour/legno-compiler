import hwlib.device as devlib
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.hcdc.hcdcv2 as hcdclib
import random
import itertools
import ops.opparse as opparse
import time
import matplotlib.pyplot as plt

import runtime.runtime_util as runtime_util

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

  def __init__(self,block,loc,output,cfg,method,n,m):
    ProfilePlanner.__init__(self,block,loc,cfg)
    self.n = n					#outer dimensions of search space
    self.m = m					#resolution (linspace) of search space
    self.block = block
    self.loc = loc
    self.output = output
    self.method = method
    self.dynamic_index = 0

  def new_hidden(self):				#hidden code is a particular set of nmos,pmos, etc
    #print(self.config["nmos"].value)
    #help(self.config)
    #print(dir(self.config["nmos"]))
    #help(self.config["nmos"])
    hidden = {}
    for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), \
                        self.block.state):
      hidden[state] = runtime_util.select_from_array(state.values,self.n)
    self._hidden_fields = list(hidden.keys())
    hidden_values = list(map(lambda k :hidden[k], self._hidden_fields))

    self.hidden_iterator = itertools.product(*hidden_values)
    self.dynamic_iterator = None
    self.dynamic_index = 0

  def next_hidden(self):
    try:
      values = next(self.hidden_iterator)
      return values
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
      dynamic[inp.name] = runtime_util.select_from_interval(inp.interval[self.config.mode],self.m)

    for data in filter(lambda dat: dat.name in variables, blk.data):
      dynamic[data.name] = runtime_util.select_from_quantized_interval(data.interval[self.config.mode],  \
                                                                    data.quantize[self.config.mode], \
                                                                    self.m)


    self._dynamic_fields = list(dynamic.keys())
    dynamic_values = list(map(lambda k :dynamic[k], self._dynamic_fields))
    self.dynamic_iterator = itertools.product(*dynamic_values)

  def next_dynamic(self):
    assert(not self.dynamic_iterator is None)
    try:
      self.dynamic_index += 1
      values = next(self.dynamic_iterator)
      return dict(zip(self._dynamic_fields,values))
    except StopIteration:
      self.dynamic_iterator = None
      return None

class SingleDefaultPointPlanner(BruteForcePlanner):

  def __init__(self,block,loc,output,method,cfg,n,m):
    BruteForcePlanner.__init__(self,block,loc,output,cfg,method, \
                               n,m)

  def new_hidden(self):
    hidden = {}
    for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), \
                        self.block.state):
      hidden[state.name] = self.config[state.name].value

    self.hidden_iterator = hidden
    self.dynamic_iterator = None

  def next_hidden(self):
    value = self.hidden_iterator
    self.hidden_iterator = None
    return value

class SingleTargetedPointPlanner(BruteForcePlanner):

  def __init__(self,block,loc,output,cfg,method,n,m,hidden_codes):
    BruteForcePlanner.__init__(self,block,loc,output, \
                               cfg,method,n,m)
    self.hidden_codes = hidden_codes

  def new_hidden(self):
    hidden = {}
    for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), self.block.state):
      hidden[state.name] = self.hidden_codes[state.name]

    self.hidden_iterator = hidden
    self.dynamic_iterator = None

  def next_hidden(self):
    value = self.hidden_iterator
    self.hidden_iterator = None
    return value

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
      print("_output_fields: ", _output_fields)
      output_values = list(map(lambda k :result[k], _output_fields))
      #print("!!!generic iterator called, returning: ", result)
    except IndexError:
      raise StopIteration
    self.index += 1
    return output_values

class RandomCodeIterator:
  def __init__(self,block,loc,config,num_codes):
    self.block = block
    self.loc = loc
    self.config = config

    self.index = num_codes


  def __iter__(self):
    return self

  def __next__(self):
    if self.index >= 0:
      hidden_codes = {}
      for state in filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), \
                          self.block.state):
        hidden_codes[state.name] = random.choice(state.values)

      self.index -= 1
      return hidden_codes

    else:
      raise StopIteration
