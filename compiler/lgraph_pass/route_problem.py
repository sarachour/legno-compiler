import compiler.lgraph_pass.vadp as vadplib 
import hwlib.device as devlib
import hwlib.block as blocklib

class BlockInstanceResource:

  def __init__(self,dev,block,loc):
    assert(isinstance(loc,devlib.Location))
    assert(isinstance(block,blocklib.Block))
    self.dev = dev
    self.block = block
    self.loc = loc

  def __repr__(self):
    return "res(%s@%s)" % (self.block.name, self.loc)

  def __eq__(self,other):
    return str(self) == str(other)

  def limit(self):
    n_instances = len(list(filter(lambda inst:  \
                          devlib.Layout.intersection(inst,self.loc.address), \
                          self.dev.layout.instances(self.block.name))))
    return n_instances

class ConnectionResource:

  def __init__(self,dev, \
                sblk,sloc,sport, \
                dblk,dloc,dport):
    self.dev = dev
    self.source_block = sblk
    self.source_loc = sloc
    self.source_port = sport
    self.dest_block = dblk
    self.dest_loc = dloc
    self.dest_port = dport

  def limit(self):
    n_src = len(list(filter(lambda inst:  \
                          devlib.Layout.intersection(inst, \
                                                    self.source_loc.address), \
                          self.dev.layout.instances(self.source_block.name))))
    n_dest = len(list(filter(lambda inst:  \
                          devlib.Layout.intersection(inst, \
                                                    self.dest_loc.address), \
                          self.dev.layout.instances(self.dest_block.name))))
    return min(n_src,n_dest)

  def __repr__(self):
    return "res((%s,%s,%s) -> (%s,%s,%s))" % (
      self.source_block.name,self.source_loc,self.source_port.name,
      self.dest_block.name,self.dest_loc,self.dest_port.name
    )



class ConnectionAssignVar:

  def __init__(self,dev, \
               sblk,sident,sport,sloc, \
                dblk,dident,dport,dloc, \
                path_id,path):
    assert(isinstance(sblk,blocklib.Block))
    assert(isinstance(dblk,blocklib.Block))
    assert(isinstance(sloc,devlib.Location))
    assert(isinstance(dloc,devlib.Location))
    self.dev = dev
    self.source_block = sblk
    self.source_ident = sident
    self.source_port = sport
    self.source_loc = sloc

    self.dest_block = dblk
    self.dest_ident = dident
    self.dest_port = dport
    self.dest_loc = dloc

    self.path = path
    self.path_id = path_id

  def __repr__(self):
    return "assign-conn((%s,%d,%s,%s,%d,%s) -> (%s,%s,%d))" \
      % (self.source_block.name,self.source_ident,self.source_port.name, \
          self.dest_block.name,self.dest_ident,self.dest_port.name, \
          self.source_loc,self.dest_loc,self.path_id)

  def resources(self):
    if len(self.path) <= 2:
      return

    for route_block,route_loc in self.path[1:-1]:
      yield BlockInstanceResource(self.dev, \
                              self.dev.get_block(route_block),
                              devlib.Location(route_loc))


    '''
    for idx,_ in enumerate(self.path[:-1]):
      src = self.path[idx]
      dst = self.path[idx+1]
      srcport = self.dev.get_block(src[0]).outputs.field_names()[0] \
                if len(src) == 2 else src[2]
      dstport = self.dev.get_block(dst[0]).inputs.field_names()[0] \
                if len(dst) == 2 else dst[2]
      yield ConnectionResource(self.dev,
                               self.dev.get_block(src[0]),
                               devlib.Location(src[1]),
                               self.dev.get_block(src[0]) \
                               .outputs[srcport],
                               self.dev.get_block(dst[0]),
                               devlib.Location(dst[1]),
                               self.dev.get_block(dst[0]) \
                               .inputs[dstport]
      )
      '''


class BlockIdentifierAssignVar:

  def __init__(self,dev,block,ident,loc):
    self.dev = dev
    self.block = block
    self.ident = ident
    self.loc = loc

  def __repr__(self):
    return "assign(%s.%d => %s)" % (self.block.name, \
                                    self.ident,
                                    self.loc)
  def resources(self):
    yield BlockInstanceResource(self.dev, \
                                self.block, \
                                self.loc)
class LocAssignments:

  def __init__(self):
    self.assignments = []
    self.by_ident = {}
    self.paths = []
    self.by_conn = {}

  def add(self,v):
    assert(isinstance(v,BlockIdentifierAssignVar))
    self.assignments.append(v)
    key = (v.block.name,v.ident)
    assert(not key in self.by_ident)
    self.by_ident[key] = v

  def add_conn(self,conn):
    key = (conn.source_block.name, \
           conn.source_ident, \
           conn.source_port, \
           conn.dest_block.name, \
           conn.dest_ident, \
           conn.dest_port)

    self.paths.append(conn)
    assert(not key in self.by_conn)
    self.by_conn[key] = conn

  def get(self,block,ident):
    return self.by_ident[(block.name,ident)]

  def get_path(self,srcblk,srcident,srcport, \
               dstblk,dstident,dstport):
    key = (
      srcblk.name,srcident,srcport,
      dstblk.name,dstident,dstport
    )
    return self.by_conn[key]
  def __iter__(self):
    for a in self.assignments:
      yield a

class RoutingProblem:


  def __init__(self,board,view,assignments=None):
    self.dev = board
    self.view = view
    self.identifier_assigns = []
    self.conn_assigns = []
    self.resources = []
    self.valid = True
    self.message = None
    self.assignments = assignments

  def fail(self,msg):
    self.message = msg
    self.valid = False


  def is_valid_instance_assignment(self,block,identifier,loc):
    if self.assignments is None:
      return True

    for assign in self.assignments:
      if assign.block.name == block.name and \
         assign.ident == identifier and \
         not devlib.Layout.intersection(assign.loc.address,loc.address) is None:
           return True

    return False


  def add_virtual_instance(self,block,identifier):
    instances = set(map(lambda full_loc: \
                    devlib.Location(self.dev.layout.prefix(full_loc,self.view)),\
                    self.dev.layout.instances(block.name)))


    if len(instances) == 0:
      self.fail(" no locations for block <%s> with identifier <%d>" \
                % (block.name,identifier))

    for loc in instances:
      if not self.is_valid_instance_assignment(block,identifier,loc):
        continue

      assign = BlockIdentifierAssignVar(self.dev, \
                                            block, \
                                            identifier, \
                                            loc)
      self.identifier_assigns \
          .append(assign)

      for res in assign.resources():
            if not res in self.resources:
              self.resources.append(res)



  def add_virtual_conn(self,sblk,sident,sport, \
                       dblk,dident,dport):

    source_idents = list(filter(lambda v: v.block.name == sblk.name and \
                           v.ident == sident,
                           self.identifier_assigns))
    dest_idents = list(filter(lambda v: v.block.name == dblk.name and \
                           v.ident == dident,
                           self.identifier_assigns))

    n_paths = 0
    for src_assign in source_idents:
      for dest_assign in dest_idents:

        for path_id,path in enumerate(devlib.distinct_paths(self.dev, \
                                               sblk.name, \
                                               src_assign.loc.address, \
                                               sport.name, \
                                               dblk.name, \
                                               dest_assign.loc.address, \
                                               dport.name)):
          assign = ConnectionAssignVar(self.dev, \
                                        sblk, \
                                        sident, \
                                        sport, \
                                        src_assign.loc, \
                                        dblk, \
                                        dident, \
                                        dport, \
                                        dest_assign.loc, \
                                        path_id, \
                                        path
                   )
          n_paths += 1
          self.conn_assigns.append(assign)
          for res in assign.resources():
            if not res in self.resources:
              self.resources.append(res)

    if n_paths == 0:
      self.fail(" no paths for conn <%s,%d,%s> -> <%s,%d,%s>" \
                % (sblk.name,sident,sport.name,dblk.name,dident,dport.name))




  def solve(self):
    raise NotImplementedError
