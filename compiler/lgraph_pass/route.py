import compiler.lgraph_pass.vadp as vadplib 

class RoutingProblem:

  def __init__(self,board,view,assignments=None):
    self.dev = board
    self.view = view
    self.assignments = None


  def solve(self):
    raise NotImplementedError

class LocAssignments:

  def __init__(self):
    pass

class LocAssignmentStack:

  def __init__(self):
    self._stack =  []


def routing_problem(board,view,vadp,assignments):
  prob = RoutingProblem(board,view,assignments)
  for vadpstmt in vadp:
    if isinstance(vadpstmt, vadplib.VADPConfig):
      print(vadpstmt)

  return prob

def route(board,vadp):
  # assign each block to a chip
  # assign each block to a tile, given chip assignments
  # assign each block to a slice, given tile assignments
  # assign each block to a index, given slice assignments
  views = board.layout.views
  assignments = LocAssignmentStack()

  adp = vadplib.to_adp(vadp)
  for idx,view in enumerate(views):
    prob = routing_problem(board,view,vadp,assignments)
    result = prob.solve()

  raise NotImplementedError
