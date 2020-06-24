import hwlib.adp as adplib
#import hwlib.config as configlib

def random_locs(board,locs,conns,restrict):
  # test this annotation.
  def test_conns(assigns,blk,fragid,loc):
    for (sblk,sfragid),sport, \
        (dblk,dfragid),dport in conns:
      sloc,dloc = None,None
      if sblk == blk and fragid == sfragid:
        sloc = loc
      elif (sblk,sfragid) in assigns:
        sloc = assigns[(sblk,sfragid)]

      if dblk == blk and fragid == dfragid:
        dloc = loc
      elif (dblk,dfragid) in assigns:
        dloc = assigns[(dblk,dfragid)]

      if sloc is None or dloc is None:
        continue

      if not board.route_exists(sblk,sloc,sport, \
                                dblk,dloc,dport):
        print("cannot connect %s[%s].%s -> %s[%s].%s" \
              % (sblk,sloc,sport,dblk,dloc,dport))
        return False
    return True

  def recurse(locs,assigns,in_use):
    if len(locs) == 0:
      yield assigns
    else:
      (blk,fragid),annot_loc = locs[0]
      if not annot_loc is None:
        new_assigns = dict(list(assigns.items()) + [((blk,fragid),annot_loc)])
        new_in_use = list(in_use) + [(blk,annot_loc)]
        for assign in recurse(locs[1:],new_assigns,new_in_use):
          yield assign

      else:
        orig_locs = list(filter(lambda loc: not (blk,loc) in in_use
                           and test_conns(assigns,blk,fragid,loc),
                           board.instances_of_block(blk)))

        print("%s[%d] = %d" % (blk,fragid,len(orig_locs)))
        if (blk,fragid) in restrict:
          prefix = restrict[(blk,fragid)]
          layer = board.sublayer(prefix[1:])
          valid_locs = list(filter(lambda loc: \
                                   layer.is_member(board.from_position_string(loc)),  \
                                   orig_locs))
          result_locs = valid_locs
        else:
          assert(len(locs) > 0)
          result_locs = orig_locs

        for loc in result_locs:
          new_assigns = dict(list(assigns.items())  \
                             + [((blk,fragid),loc)])
          new_in_use = list(in_use) + [(blk,loc)]
          for assign in recurse(locs[1:],new_assigns,new_in_use):
            yield assign

  for assigns in recurse(list(locs.items()), {}, []):
    result = {}
    for key,loc in assigns.items():
      result[key] = board.from_position_string(loc)
    yield result




def find_routes(board,locs,conns,inst_assigns):
  def to_conns(route):
    result = []
    for i in range(0,len(route)-1):
      sb,sl,sp = route[i]
      db,dl,dp = route[i+1]
      # internal connection
      if sb == db and sl == dl:
        continue
      result.append([(sb,sl,sp),(db,dl,dp)])
    return result

  def recurse(in_use,routes,remaining_conns):
    if len(remaining_conns) == 0:
      yield routes

    else:
      (sblk,sfragid),sport,(dblk,dfragid),dport = remaining_conns[0]
      sloc = board.position_string(inst_assigns[(sblk,sfragid)])
      dloc = board.position_string(inst_assigns[(dblk,dfragid)])
      n_routes = 0
      for route in board.find_routes(sblk,sloc,sport,dblk,dloc,dport, \
                                     count=1000):
        double_use = list(filter(lambda place: place in in_use, route))
        if len(double_use) > 0:
          continue

        print("[%d] %s[%s].%s -> %s[%s].%s" % (len(remaining_conns), \
                                               sblk,sloc,sport,dblk,dloc,dport))
        n_routes += 1
        new_routes = list(routes)
        new_routes.append(to_conns(route))
        new_in_use = list(in_use) + route[1:-1]

        for solution in recurse(new_in_use,  \
                                new_routes,  \
                                remaining_conns[1:]):
          yield solution


  def sort_conns(conns):
    lengths = {}
    for conn in conns:
      (sblk,sfragid),sport,(dblk,dfragid),dport= conn
      sloc = board.position_string(inst_assigns[(sblk,sfragid)])
      dloc = board.position_string(inst_assigns[(dblk,dfragid)])
      for route in board.find_routes(sblk,sloc,sport,dblk,dloc,dport,
                                     count=1000):
        lengths[conn] = len(route)
        break

      assert(conn in lengths)

    new_conns = sorted(conns, key=lambda c: -lengths[c])
    assert(len(new_conns) == len(conns))
    return new_conns

  new_conns = sort_conns(conns)
  for solution in recurse([],[],new_conns):
    yield solution



def make_concrete_circuit(board,routes,inst_assigns,configs):
  adp = adplib.AnalogDeviceProg(board)
  for (blk,fragid),loc in inst_assigns.items():
    locstr = board.position_string(loc)
    adp.use(blk,locstr,configs[(blk,fragid)])

  for route in routes:
    for (sblk,sloc,sport),(dblk,dloc,dport) in route:
      if not adp.in_use(sblk,sloc):
        cfg = configlib.Config()
        cfg.set_comp_mode("*")
        adp.use(sblk,sloc,cfg)
      if not adp.in_use(dblk,dloc):
        cfg = configlib.Config()
        cfg.set_comp_mode("*")
        adp.use(dblk,dloc,cfg)

      adp.conn(sblk,sloc,sport,dblk,dloc,dport)

  return adp

