import hwlib.block as blocklib

class Location:

  def __init__(self,address):
    self.address = address

  def to_json(self):
    return self.address

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
    assert(isinstance(blk,blocklib.Block))
    assert(not blk.name in self._blocks)
    self._blocks[blk.name] = blk

  def get_block(self,name):
    if not name in self._blocks:
      raise Exception("no block found with name <%s>" % name)
    return self._blocks[name]

  @property
  def blocks(self):
    return self._blocks.values()
