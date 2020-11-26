import compiler.lgraph_pass.vadp as vadplib 
import compiler.lgraph_pass.route_solver as route_solver
import compiler.lgraph_pass.route_problem as routeproblib
import hwlib.device as devlib
import hwlib.block as blocklib

class LocAssignmentStack:

  class Entry:

    def __init__(self,assigns):
      assert(isinstance(assigns,routeproblib.LocAssignments))
      self.assigns = assigns
      self.negations = []

    def add_negation(self,neg):
      assert(isinstance(neg,routeproblib.LocAssignments))
      self.negations.append(neg)

  def __init__(self):
    self._stack =  []

  @property
  def ptr(self):
    return len(self._stack)

  def top(self):
    if len(self._stack) == 0:
      return None
    else:
      return self._stack[-1]

  def push(self,v):
    assert(isinstance(v,LocAssignmentStack.Entry))
    assert(not v is None)
    self._stack.append(v)

  def pop(self):
    if len(self._stack) == 0:
      return

    tmp = self._stack[:-1]
    self._stack = tmp

def routing_problem(board,view,vadp,entry):
  if not entry is None:
    prob = routeproblib.RoutingProblem(board,view, \
                                       entry.assigns, \
                                       entry.negations)

  else:
    prob = routeproblib.RoutingProblem(board,view)

  for vadpstmt in vadp:
    if isinstance(vadpstmt, vadplib.VADPConfig):
      prob.add_virtual_instance(vadpstmt.target.block, \
                                vadpstmt.target.ident)

  for vadpstmt in vadp:
    if isinstance(vadpstmt, vadplib.VADPConn):
      prob.add_virtual_conn(vadpstmt.source.block, \
                            vadpstmt.source.ident, \
                            vadpstmt.source.port, \
                            vadpstmt.sink.block, \
                            vadpstmt.sink.ident, \
                            vadpstmt.sink.port)

  print("# instance vars: %s" % len(prob.identifier_assigns))
  print("# conn vars: %s" % len(prob.conn_assigns))
  print("# resources: %s" % len(prob.resources))

  return prob

def use_route_blocks(dev,used_route_blocks,conn_assign):
  path = conn_assign.path
  vadpstmts = []
  if len(path) <= 2:
    return vadpstmts,list(path)

  new_path = list(path)
  for idx,(route_block,route_inst_pattern) in enumerate(path[1:-1]):
    blk = dev.get_block(route_block)
    assert(len(blk.modes) == 1)
    assert(len(blk.state) == 0)
    assert(len(blk.data) == 0)
    # get first compatible instance that has not been used yet
    try:
      inst = next(inst for inst in dev.layout.instances(route_block) \
                  if not devlib.Layout \
                  .intersection(inst,route_inst_pattern) is None and \
                  (route_block,inst) not in used_route_blocks )

      new_path[1+idx]= (route_block,inst)
      used_route_blocks.append((route_block,inst))
      target_port = vadplib.PortVar(blk,devlib.Location(inst))
      stmt = vadplib.VADPConfig(target_port,blk.modes)
      stmt.target.ident = devlib.Location(inst)
      vadpstmts.append(stmt)
    except StopIteration as e:
      raise Exception("no instances for route block <%s>" % route_block)

  return vadpstmts,new_path

def generate_vadp_fragment_for_path(dev,route_block_instances,conn_assign):
  def get_route_input(blk):
    name = blk.inputs.field_names()[0]
    return blk.inputs[name]

  def get_route_output(blk):
    name = blk.outputs.field_names()[0]
    return blk.outputs[name]

  vadp_config_stmts, path = use_route_blocks(dev, \
                                             route_block_instances, \
                                             conn_assign)
  for stmt in vadp_config_stmts:
    yield stmt

  for idx in range(0,len(path)-1):
    src_tuple = path[idx]
    dest_tuple = path[idx+1]
    assert(not devlib.Layout.is_pattern(src_tuple[1]))
    assert(not devlib.Layout.is_pattern(dest_tuple[1]))
    srcblk = dev.get_block(src_tuple[0])
    src = vadplib.PortVar(srcblk, \
                  devlib.Location(src_tuple[1]), \
                  srcblk.outputs[src_tuple[2]] \
                  if len(src_tuple) == 3 else \
                  get_route_output(srcblk)
    )
    destblk = dev.get_block(dest_tuple[0])
    dest = vadplib.PortVar(destblk, \
                  devlib.Location(dest_tuple[1]), \
                  destblk.inputs[dest_tuple[2]] \
                  if len(dest_tuple) == 3 else \
                  get_route_input(destblk)
    )
    yield vadplib.VADPConn(src,dest)


def finalize(board,vadp,assigns):
  new_vadp = []
  # route block instances in use
  route_block_instances = []
  for stmt in vadp:
    if isinstance(stmt,vadplib.VADPConfig):
      assign = assigns.get(stmt.target.block,stmt.target.ident)
      new_stmt = stmt.copy()
      new_stmt.target.ident = assign.loc
      assert(isinstance(new_stmt.target.ident,devlib.Location))
      new_vadp.append(new_stmt)

    elif isinstance(stmt,vadplib.VADPSource):
      assign = assigns.get(stmt.target.block,stmt.target.ident)
      new_stmt = stmt.copy()
      new_stmt.target.ident = assign.loc
      assert(isinstance(new_stmt.target.ident,devlib.Location))
      new_vadp.append(new_stmt)

  for stmt in vadp:
    if isinstance(stmt,vadplib.VADPConn):
      srcloc = assigns.get(stmt.source.block, \
                        stmt.source.ident).loc
      sinkloc = assigns.get(stmt.sink.block, \
                            stmt.sink.ident).loc

      path = assigns.get_path(
        stmt.source.block,stmt.source.ident,stmt.source.port,
        stmt.sink.block,stmt.sink.ident,stmt.sink.port
      )

      frag = list(generate_vadp_fragment_for_path(board, \
                                                  route_block_instances, \
                                                  path))
      new_vadp += frag



  return new_vadp

def route_next_solution(board,vadp,assign_stack):
  views = board.layout.views
  while assign_stack.ptr <= len(views)-1 and assign_stack.ptr >= 0:
    print("--> routing view %s" % views[assign_stack.ptr])
    view = views[assign_stack.ptr]
    # build routing problem
    prob = routing_problem(board,view,vadp, \
                           assign_stack.top())
    assigns = route_solver.solve(prob)
    if assigns is None:
      assign_stack.pop()
    else:
      assert(not assigns is None)
      assign_stack.push(LocAssignmentStack.Entry(assigns))

  if assign_stack.top() is None:
    return None
  else:
    return assign_stack.top()



def route(board,vadp):
  # assign each block to a chip
  # assign each block to a tile, given chip assignments
  # assign each block to a slice, given tile assignments
  # assign each block to a index, given slice assignments
  assign_stack = LocAssignmentStack()

  has_solution = True
  negations = []
  while has_solution:
    result = route_next_solution(board,vadp,assign_stack)
    if not result is None:
      yield finalize(board,vadp,result.assigns)
      # remove result
      assign_stack.pop()
      assign_stack.top().add_negation(result.assigns)
    else:
      has_solution = False
