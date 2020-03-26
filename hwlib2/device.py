

class Location:

  def __init__(self,layout,address):
    self.address = address
    self.layout = layout

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

  
