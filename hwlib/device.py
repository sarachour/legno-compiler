import hwlib.block as blocklib
import itertools

class Location:
  WILDCARD = "*"

  def __init__(self,address):
    assert(all(map(lambda item: isinstance(item,int) or \
                   item == Location.WILDCARD, \
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

  def __hash__(self):
    return hash(str(self))

  def __eq__(self,loc):
    if not (isinstance(loc,Location)):
      raise Exception("cannot compare %s with %s" % (self,loc))
    return str(loc) == str(self)

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

  @staticmethod
  def is_pattern(loc):
    for l in loc:
      if l == Layout.WILDCARD:
        return True
    return False

  @staticmethod
  def intersection(loc1,loc2):
    isect = []
    for l1,l2 in zip(loc1,loc2):
      if l1 == l2:
        isect.append(l1)
      elif l1 == Layout.WILDCARD:
        isect.append(l2)
      elif l2 == Layout.WILDCARD:
        isect.append(l1)
      else:
        return None

    return isect

  @property
  def views(self):
    return self._views

  @views.setter
  def views(self,views):
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

  def prefix(self,loc,view):
    idx = self._views.index(view)
    assert(idx >= 0)
    return loc[:idx+1]

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

  def get_connections(self,sblk,sport,dblk,dport):
    if not (sblk,sport) in self._src2sink:
      raise Exception("no connection originating from: (%s,%s)" % (sblk,sport))
    if not (dblk,dport) in self._src2sink[(sblk,sport)]:
      raise Exception("no connection originating at (%s,%s) and ending at (%s,%s)" % (sblk,sport,dblk,dport))

    for sloc,dloc in self._src2sink[(sblk,sport)][(dblk,dport)]:
      yield sloc,dloc



  @property
  def connections(self):
    for sblk,sport in self._src2sink.keys():
      for dblk,dport in self._src2sink[(sblk,sport)].keys():
        for sloc,dloc in self._src2sink[(sblk,sport)][(dblk,dport)]:
          yield sblk,sloc,sport,dblk,dloc,dport


  @property
  def get_connection_sources(self):
    for sblk,sport in self._src2sink.keys():
      yield sblk,sport


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

class PinInfo:

  def __init__(self,pin,block,loc,port,chan):
    self.channel = chan
    self.block = block
    self.port = port
    self.pin = pin
    self.loc = loc

  def match(self,block,loc,port):
    if block.name == self.block.name and \
       loc == self.loc and \
       port == self.port:
      return True
    return False


class Device:
  
  def __init__(self,name):
    self.name = name
    self._blocks = {}
    self.layout = Layout(self)
    self._pins = {}
    self.time_constant = 1.0
    self.physdb = None

  def set_external_pin(self,pin_id,block,loc,port,chan):
    assert(not pin_id in self._pins)
    assert(block.name in self._blocks)
    self._pins[pin_id] = PinInfo(pin_id,block,loc,port,chan)

  def get_external_pins(self,block,loc,port):
    for pin in self._pins.values():
      if pin.match(block,loc,port):
        yield pin

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

def path_exists(dev,sblk,sport,dblk,dport, \
                num_route_blocks=4):
  route_blocks = []
  interim_paths = []
  start_paths = []
  end_paths = []
  for blk in dev.blocks:
    if blk.type == blocklib.BlockType.ROUTE:
      assert(len(blk.inputs) == 1)
      assert(len(blk.outputs) == 1)
      route_blocks.append(blk.name)


  for csblk,csloc,csport, \
      cdblk,cdloc,cdport in dev.layout.connections:
    # internal edge on path
    if csblk in route_blocks and cdblk in route_blocks and \
       not (csblk,cdblk) in interim_paths:
      interim_paths.append((csblk,cdblk))

    # ending edge on path
    elif csblk in route_blocks and cdblk == dblk and \
         cdport == dport and not (csblk,cdblk,cdport) in end_paths:
      end_paths.append((csblk, \
                        cdblk,cdport))
    # starting edge on path
    elif cdblk in route_blocks and csblk == sblk and \
         csport == sport and not (csblk,csport,cdblk) in start_paths:
      start_paths.append((csblk,csport, \
                          cdblk))



  # return if there's a direct connection without route blocks
  def has_direct_connection():
    try:
      for sl,dl in dev.layout.get_connections(sblk,sport, \
                                              dblk,dport):
        return True
      return False
    except Exception as e:
      return False

  # walk over paths, starting from shortest
  def walk_paths(curr_path):
    if len(curr_path) - 2 >= num_route_blocks:
      return

    if len(curr_path) == 0:
      if has_direct_connection():
          yield [(sblk,sport),(dblk,dport)]

      for sb,sp,db in start_paths:
        for path in walk_paths([(sb,sp),(db)]):
          yield path

    else:
      db = curr_path[-1]
      for csb,cdb,cdp in end_paths:
        if csb == db:
          new_path = list(curr_path)
          new_path.append((cdb,cdp))
          yield new_path

      # find
      for csb,cdb in interim_paths:
        if csb == db:
          new_path = list(curr_path)
          new_path.append((cdb))
          for path in walk_paths(new_path):
            yield path

  # enumerate all paths
  for path in walk_paths([]):
    return True
  return False


def distinct_paths(dev,sblk,sloc,sport,dblk,dloc,dport, \
                   num_route_blocks=4):
  route_blocks = []
  interim_paths = []
  start_paths = []
  end_paths = []
  for blk in dev.blocks:
    if blk.type == blocklib.BlockType.ROUTE:
      assert(len(blk.inputs) == 1)
      assert(len(blk.outputs) == 1)
      route_blocks.append(blk.name)

  for csblk,csloc,csport, \
      cdblk,cdloc,cdport in dev.layout.connections:
    # internal edge on path
    if csblk in route_blocks and cdblk in route_blocks:
      interim_paths.append((csblk,csloc, \
                            cdblk,cdloc))
    # ending edge on path
    elif csblk in route_blocks and cdblk == dblk and \
         cdport == dport:
      cdloc = Layout.intersection(cdloc,dloc)
      if not cdloc is None:
        end_paths.append((csblk,csloc, \
                          cdblk,cdloc,cdport))
    # starting edge on path
    elif cdblk in route_blocks and csblk == sblk and \
         csport == sport:
      csloc = Layout.intersection(csloc,sloc)
      if not csloc is None:
        start_paths.append((csblk,csloc,csport, \
                            cdblk,cdloc))


  # return if there's a direct connection without route blocks
  def has_direct_connection():
    try:
      direct_connections = False
      for sl,dl in dev.layout.get_connections(sblk,sport, \
                                                dblk,dport):
        dl = Layout.intersection(dl,dloc)
        sl = Layout.intersection(sl,sloc)
        if not dl is None and not sl is None:
          direct_connections = True
          break

      return direct_connections
    except Exception as e:
      return False

  # walk over paths, starting from shortest
  def walk_paths(curr_path):
    if len(curr_path) - 2 >= num_route_blocks:
      return

    if len(curr_path) == 0:
      if has_direct_connection():
          yield [(sblk,sloc,sport),(dblk,dloc,dport)]

      for sb,sl,sp,db,dl in start_paths:
        for path in walk_paths([(sb,sl,sp),(db,dl)]):
          yield path

    else:
      db,dl = curr_path[-1]
      for csb,csl,cdb,cdl,cdp in end_paths:
        if csb == db and \
           not Layout.intersection(csl,dl) is None:
          new_dl = Layout.intersection(dl,csl)
          new_path = list(curr_path)
          new_path[-1] = (db,new_dl)
          new_path.append((cdb,cdl,cdp))
          yield new_path

      # find
      for csb,csl,cdb,cdl in interim_paths:
        if csb == db and \
           not Layout.intersection(csl,dl) is None:
          new_dl = Layout.intersection(dl,csl)
          new_path = list(curr_path)
          new_path[-1] = (db,new_dl)
          new_path.append((cdb,cdl))
          for path in walk_paths(new_path):
            yield path


  # enumerate all paths
  for path in walk_paths([]):
    yield path

