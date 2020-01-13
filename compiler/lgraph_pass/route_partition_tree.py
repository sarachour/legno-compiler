import networkx as nx

def count_edges(graph,A,B):
  count = 0
  for (sblk,sfrag),(dblk,dfrag) in graph.edges:
    if (sblk,sfrag) in A and \
       (dblk,dfrag) in B:
      count += 1
    if (sblk,sfrag) in A and \
       (dblk,dfrag) in B:
      count += 1

  return count


class PartNode:

  def __init__(self,n,left,right):
    self.left = left
    self.right = right
    self.n = n

  def nodes(self):
    return self.left.nodes() \
      + self.right.nodes()


  def divide(self,groups):
    le = self.left.n
    re =self.right.n

    if groups == 1:
      return [self]

    if groups % 2 == 0:
      gs1=self.left.divide(int(groups/2))
      gs2=self.right.divide(int(groups/2))
    else:
      gs1=self.left.divide(math.floor(groups/2)+1)
      gs2=self.right.divide(math.floor(groups/2))

    return gs1+gs2


  def depth(self):
    return 1+max(self.left.depth(),self.right.depth())

  def edges(self):
    return self.left.edges() + self.right.edges() + self.n


  def to_string(self,halt,depth):
    s = "\t"*depth + ("part(c=%d,n=%d)\n" % (self.n,len(self.nodes())))
    if halt > 0 and depth < halt:
      s += self.left.to_string(halt,depth+1)
      s += self.right.to_string(halt,depth+1)
    return s

  def __repr__(self):
    return to_string(self,-1,depth)

class LeafNode:

  def __init__(self,blk,loc):
    self.block = blk
    self.loc = loc
    self.n = 0

  def depth(self):
    return 0

  def edges(self):
    return 0

  def divide(self,n):
    return [self]

  def to_string(self,halt,depth):
    return "node(%s,%s)" % (self.block,self.loc)

  def nodes(self):
    return [(self.block,self.loc)]

def build_partition_tree(board,locs,conns):
  def partition(g):
    A,B = nx.algorithms.community \
                       .kernighan_lin_bisection(g)
    n = count_edges(g,A,B)
    if len(A) > 1:
      Ag = g.subgraph(A)
      left = partition(Ag)
    else:
      blk,fragid = next(iter(A))
      left = LeafNode(blk,fragid)

    if len(B) > 1:
      Bg = g.subgraph(B)
      right = partition(Bg)
    else:
      blk,fragid = next(iter(B))
      right = LeafNode(blk,fragid)

    return PartNode(n,left,right)

  graph = nx.Graph()
  for blk,frag in locs.keys():
    graph.add_node((blk,frag))

  for (sblk,sfrag),sport,(dblk,dfrag),dport in conns:
    graph.add_edge((sblk,sfrag),(dblk,dfrag))

  part_tree = partition(graph)
  return part_tree

def greedy_partition(part_tree,locs):
  nodes = part_tree.divide(len(locs))
  print(part_tree.to_string(halt=3,depth=0))
  groups = []
  for node_i in nodes:
    group = []
    for blk,frag in node_i.nodes():
      group.append((blk,frag))

    groups.append(group)

  return groups
