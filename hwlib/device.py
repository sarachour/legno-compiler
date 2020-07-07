import hwlib.block as blocklib
import itertools

class Location:

  def __init__(self,address):
    assert(all(map(lambda item: isinstance(item,int), \
                   address)))
    self.address = address

  def to_json(self):
    return self.address

  @staticmethod
  def from_json(addr):
    return Location(addr)

  @staticmethod
  def from_string(string):
    argstr = string.split("loc(")[1].split(")")[0]
    addr = list(map(lambda arg: int(arg), \
                    argstr.split(",")))
    return Location(addr)

  def __str__(self):
    tup = ",".join(map(lambda i: str(i), self.address))
    return "loc(%s)" % (tup)

  def __len__(self):
    return len(self.address)

class Layer:

  def __init__(self):
    pass


class Layout:
  WILDCARD = "*"

  def __init__(self,dev):
    self._dev = dev
    self._views = []
    self._locs = {}
    self._blocks = {}
    self._src2sink = {}
    self._sink2src = {}

  def set_views(self,views):
    self._views = views

  def view_list(self,view):
    idx = self._views.index(view)
    return self._views[:idx+1]

  def valid_loc(self,loc):
    if len(loc) > len(self._views):
      return False

    for view,idx in zip(self._views,loc):
      if not idx in self._locs[view] and not \
         idx == Layout.WILDCARD:
        return False
    return True

  def connect(self,sblk,sloc,sport,dblk,dloc,dport):
    self._dev.get_block(sblk).outputs[sport]
    self._dev.get_block(dblk).inputs[dport]
    assert(self.valid_loc(dloc))
    assert(self.valid_loc(sloc))
    if not (sblk,sport) in self._src2sink:
      self._src2sink[(sblk,sport)] = {}
    if not (dblk,dport) in self._src2sink[(sblk,sport)]:
      self._src2sink[(sblk,sport)][(dblk,dport)] = []
    self._src2sink[(sblk,sport)][(dblk,dport)].append((sloc,dloc))

    if not (dblk,dport) in self._sink2src:
      self._sink2src[(dblk,dport)] = {}
    if not (sblk,sport) in self._sink2src[(dblk,dport)]:
      self._sink2src[(dblk,dport)][(sblk,sport)] = []

    self._sink2src[(dblk,dport)][(sblk,sport)].append((dloc,sloc))


  def instances(self,block_name):
    assert(block_name in self._blocks)
    for loc in self._blocks[block_name]:
      yield loc

  def block_at(self,block_name,loc):
    self._dev.get_block(block_name)
    if not block_name in self._blocks:
      self._blocks[block_name] = []
    assert(self.valid_loc(loc))
    self._blocks[block_name].append(loc)

  def locs(self,name):
    indices = list(map(lambda view : self._locs[view], \
                       self.view_list(name)))
    for combo in itertools.product(*indices):
      yield list(combo)

  def add_locs(self,locname,indices):
    assert(locname in self._views)
    self._locs[locname] = indices

class Device:

  def __init__(self):
    self._blocks = {}
    self.layout = Layout(self)

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
