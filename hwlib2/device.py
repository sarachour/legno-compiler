

class Location:

  def __init__(self,address):
    self.address = address

  def __str__(self):
    tup = ",".join(map(lambda i: str(i), self.address))
    return "loc(%s)" % (tup)

  def __len__(self):
    return len(self.address)

class Layer:

  def __init__(self):
    pass


class Layout:

  def __init__(self):
    self.layers = []

class Device:

  def __init__(self):
    self._blocks = {}

  def add_block(self,blk):
    assert(not blk.name in self._blocks)
    self._blocks[blk.name] = blk

  def get_block(self,name):
    return self._blocks[name]
