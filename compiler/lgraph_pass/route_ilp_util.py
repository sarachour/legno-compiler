
class RoutingEnv:

  def __init__(self,board,instances,connections,layers,assigns):
    self.board = board
    self.instances = instances
    self.connections = connections
    self.assigns = assigns
    self.layers = layers
    print("-> compute groups")
    self.groups = list(map(lambda layer: \
                    tuple(layer.position), self.layers))
    self.straddling = {}
    self.straddling_connections = {}

    print(self.groups)
    # compute possible connections.
    locmap = {}
    for locstr in set(map(lambda args: args[1], board.instances())):
      grp = self.loc_to_group(locstr)
      locmap[locstr] = grp


    self.widths = {}
    by_group = dict(map(lambda g: (g,{'src':{},'dest':{}}), self.groups))
    for (sblk,sport),(dblk,dport),locs in board.connection_list():
      for sloc,dloc in filter(lambda args: \
                              locmap[args[0]] != locmap[args[1]], locs):
        sgrp = locmap[sloc]
        dgrp = locmap[dloc]
        key = (sblk,sgrp,dblk,dgrp)
        if not (sblk,sport) in by_group[sgrp]['src']:
          by_group[sgrp]['src'][(sblk,sport)] = []

        by_group[sgrp]['src'][(sblk,sport)].append(sloc)

        if not (dblk,dport) in by_group[dgrp]['dest']:
          by_group[dgrp]['dest'][(dblk,dport)] = []

        by_group[dgrp]['dest'][(dblk,dport)].append(dloc)

        if not key in self.widths:
          self.widths[key] = []
        if not dloc in self.widths[key]:
          self.widths[key].append((dloc))

    # compute quantities
    print("-> compute counts")
    self.counts = {}
    for layer in self.layers:
      group = tuple(layer.position)
      for blk in board.blocks:
        n = len(list(board.block_locs(layer,blk.name)))
        self.counts[(group,blk.name)] = n


    print("-> compute reachable")
    self.connectivities = {}
    for layer in self.layers:
      group = tuple(layer.position)
      for blk in board.blocks:
        if self.counts[(group,blk.name)] == 0:
          continue

        loc = list(board.block_locs(layer,blk.name))[0]
        for dport in blk.inputs:
          sinks = []
          for (sblk,sport),slocs in by_group[group]['src'].items():
            for sloc in slocs:
              if board.route_exists(sblk,sloc,sport,\
                                    blk.name,loc,dport) \
                                    and not sblk in sinks:
                  sinks.append(sblk)
                  break

          self.connectivities[(blk.name,group,dport)] = sinks

        for sport in blk.outputs:
          sources= []
          for (dblk,dport),dlocs in by_group[group]['dest'].items():
            for dloc in dlocs:
              if board.route_exists(blk.name,loc,sport,
                                    dblk,dloc,dport) \
                                    and not dblk in sources:
                sources.append(dblk)
                break;

          self.connectivities[(blk.name,group,sport)] = sources


  def loc_to_group(self,loc):
    matches = list(filter(lambda ch: ch.is_member(
      self.board.from_position_string(loc)
    ), self.layers))
    if not (len(matches) == 1):
      raise Exception("%s: <%d matches>" % (loc,len(matches)))
    return tuple(matches[0].position)
