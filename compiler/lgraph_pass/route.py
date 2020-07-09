import compiler.lgraph_pass.vadp as vadplib 
import compiler.lgraph_pass.route_solver as route_solver
from compiler.lgraph_pass.route_problem import RoutingProblem
import hwlib.device as devlib
import hwlib.block as blocklib

class LocAssignmentStack:

  def __init__(self):
    self._stack =  []

  def top(self):
    if len(self._stack) == 0:
      return None
    else:
      return self._stack[-1]

  def push(self,v):
    self._stack.append(v)

  def pop(self):
    if len(self._stack) == 0:
      return

    tmp = self._stack[:-1]
    self._stack = tmp

def routing_problem(board,view,vadp,assignments):
  prob = RoutingProblem(board,view,assignments)
  for vadpstmt in vadp:
    if isinstance(vadpstmt, vadplib.VADPConfig):
      print(vadpstmt)
      prob.add_virtual_instance(vadpstmt.block, \
                                vadpstmt.ident)

  for vadpstmt in vadp:
    if isinstance(vadpstmt, vadplib.VADPConn):
      print(vadpstmt)
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

def generate_vadp_fragment_for_path(dev,conn_assign):
  def get_route_input(blk):
    name = blk.inputs.field_names()[0]
    return blk.inputs[name]

  def get_route_output(blk):
    name = blk.outputs.field_names()[0]
    return blk.outputs[name]

  path = conn_assign.path
  for idx in range(0,len(path)-1):
    src_tuple = path[idx]
    dest_tuple = path[idx+1]

    srcblk = dev.get_block(src_tuple[0])
    src = vadplib.PortVar(srcblk, \
                  devlib.Location(src_tuple[1]), \
                  srcblk.outputs[src_tuple[2]] \
                  if len(src_tuple) == 3 else \
                  get_route_output(srcblk)
    )
    destblk = dev.get_block(src_tuple[0])
    dest = vadplib.PortVar(destblk, \
                  devlib.Location(dest_tuple[1]), \
                  destblk.inputs[dest_tuple[2]] \
                  if len(dest_tuple) == 3 else \
                  get_route_output(destblk)
    )
    yield vadplib.VADPConn(src,dest)


def finalize(board,vadp,assigns):
  new_vadp = []
  for stmt in vadp:
    if isinstance(stmt,vadplib.VADPConfig):
      assign = assigns.get(stmt.block,stmt.ident)
      new_stmt = stmt.copy()
      new_stmt.ident = assign.loc
      assert(isinstance(new_stmt.ident,devlib.Location))
      new_vadp.append(new_stmt)

    elif isinstance(stmt,vadplib.VADPSource):
      assign = assigns.get(stmt.port.block,stmt.port.ident)
      new_stmt = stmt.copy()
      new_stmt.port.ident = assign.loc
      assert(isinstance(new_stmt.port.ident,devlib.Location))
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

      frag = list(generate_vadp_fragment_for_path(board,path))
      new_vadp += frag



  return new_vadp

def route(board,vadp):
  # assign each block to a chip
  # assign each block to a tile, given chip assignments
  # assign each block to a slice, given tile assignments
  # assign each block to a index, given slice assignments
  views = board.layout.views
  assign_stack = LocAssignmentStack()

  idx = 1
  while idx <= len(views)-1 and idx >= 0:
    view = views[idx]
    prob = routing_problem(board,view,vadp, \
                           assign_stack.top())
    assigns = route_solver.solve(prob)
    if assigns is None:
      assign_stack.pop()
      idx -= 1
    else:
      assign_stack.push(assigns)
      idx += 1

  if assigns is None:
    assign_stack.pop()
  else:
    assign_stack.push(assigns)

  if idx < 0 or assign_stack.top() is None:
    return None
  else:
    return finalize(board,vadp,assign_stack.top())


