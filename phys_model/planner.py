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
    hidden = {}
    for state in filter(lambda st: isinstance(st.impl, \
                                              blocklib.BCCalibImpl), \
                        self.block.state):
      hidden[state] = phys_util.select_from_array(state.values,n)


    self._hidden_fields = list(hidden.keys())
    hidden_values = list(map(lambda k :hidden[k], \
                             self._hidden_fields))
    self.hidden_iterator = itertools.product(*hidden_values)
    self.dynamic_iterator = None
    self.m = m

  def next_hidden(self):
    try:
      values = next(self.hidden_iterator)
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
      dynamic[data] = phys_util.select_from_quantized_interval(data.interval[self.config.mode], \
                                                     data.quantize[self.config.mode], self.m)

    self._dynamic_fields = list(dynamic.keys())
    dynamic_values = list(map(lambda k :dynamic[k], \
                              self._dynamic_fields))
    self.dynamic_iterator = itertools.product(*dynamic_values)

  def next_dynamic(self):
    assert(not self.dynamic_iterator is None)
    try:
      values = next(self.dynamic_iterator)
      return dict(zip(self._dynamic_fields,values))
    except StopIteration:
      self.dynamic_iterator = None
      return None
