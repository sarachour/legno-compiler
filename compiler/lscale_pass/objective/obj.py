
class LScaleObjectiveFunction():

  def __init__(self,obj,cstrs=[],tag=None):
    self._cstrs = cstrs
    self._obj = obj
    self._tag = tag
 
  def tag(self):
    if self._tag is None:
      return self.name()
    else:
      return self._tag

  @staticmethod
  def name():
    raise NotImplementedError

  def constraints(self):
    return self._cstrs

  def objective(self):
    return self._obj

