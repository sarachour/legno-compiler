
import logging
import networkx as nx
import matplotlib.pyplot as plt

import ops.ilpop as ilpop
import hwlib.abs as acirc
import hwlib.block as blocklib
import hwlib.adp as adplib
import hwlib.config as configlib
import compiler.lgraph_pass.route_ilp_util as route_ilp_util
import compiler.lgraph_pass.route_partition_tree as partition_tree
import compiler.lgraph_pass.route_find_slices as find_slices

logger = logging.getLogger('arco_route')
logger.setLevel(logging.DEBUG)


def get_sublayers(parent_layers):
  layers = []
  for parent_layer in parent_layers:
    layers += list(map(lambda i: parent_layer.layer(i), \
                       parent_layer.identifiers()))

  return layers

def ilp_instance_cstr(ilpenv,renv,groups=None):
  # create group-conn hot coding
  by_block_group = {}

  for (blk,frag_id),loc in renv.instances.items():
    choices = []
    #print("-> limit components to layer")
    if (blk,frag_id) in renv.assigns:
      prefix = renv.assigns[(blk,frag_id)]
      par_layer = renv.board.sublayer(prefix[1:])
      #print("limit %s[%s] : %s" %(blk,frag_id,prefix))
    else:
      par_layer = None

    for grp in renv.groups:
      if not par_layer is None and \
         not par_layer.is_member(grp):
        #print("%s[%d] is concretized" % (blk,frag_id))
        continue

      if renv.counts[(grp,blk)] == 0:
        print("%s not in %s" % (blk,grp))
        continue

      instvar = ilpenv.decl(('inst',blk,frag_id,grp),
                            ilpop.ILPEnv.Type.BOOL)
      print(('inst',blk,frag_id,grp))
      choices.append(instvar)
      if not (blk,grp) in by_block_group:
        by_block_group[(blk,grp)] = []
      by_block_group[(blk,grp)].append(instvar)

      if not loc is None:
        grp2 = renv.loc_to_group(loc)
        if grp == grp2:
          ilpenv.eq(ilpop.ILPVar(instvar), ilpop.ILPConst(1))
        else:
          ilpenv.eq(ilpop.ILPVar(instvar), ilpop.ILPConst(0))

    if len(choices) == 0:
      ilpenv.fail("no options for %s[%s]" % (blk,frag_id))
      return

    ilpenv.eq(
      ilpop.ILPMapAdd(
        list(map(lambda v: ilpop.ILPVar(v), choices))
      ),
      ilpop.ILPConst(1.0)
    )

  # ensure that no more than the available components are used.
  for (blk,grp),ilpvars in by_block_group.items():
    clauses = list(map(lambda v: ilpop.ILPVar(v), ilpvars))
    n = renv.counts[(grp,blk)]
    ilpenv.lte(ilpop.ILPMapAdd(clauses), ilpop.ILPConst(n))

  if not groups is None:
    for group_id,group in enumerate(groups):
      groupvars = []
      for pos in renv.groups:
        groupvar = ilpenv.decl(('grp',group_id,pos),
                               ilpop.ILPEnv.Type.BOOL)
        groupvars.append(groupvar)
        for blk,frag_id in group:
          if ilpenv.has_ilpvar(('inst',blk,frag_id,pos)):
            instvar = ilpenv.get_ilpvar(('inst',blk,frag_id,pos))
            ilpenv.eq(ilpop.ILPVar(groupvar),ilpop.ILPVar(instvar))
          else:
            ilpenv.eq(ilpop.ILPVar(groupvar),ilpop.ILPConst(0))


    ilpenv.eq(
      ilpop.ILPMapAdd(
        list(map(lambda v: ilpop.ILPVar(v), groupvars))
      ),
      ilpop.ILPConst(1.0)
    )

def ilp_single_connection_cstr(ilpenv,renv,conn_id,conn,by_straddle):
  board = renv.board
  # the connection.
  ((sblkname,sfragid),sport, \
   (dblkname,dfragid),dport) = conn

  sblk = board.block(sblkname)
  dblk = board.block(dblkname)

  by_group = {}

  for grp1 in renv.groups:
    for grp2 in renv.groups:
      # this block fragment is constrained in a way where it can't be in this group
      if not ilpenv.has_ilpvar(('inst',sblkname,sfragid,grp1)):
        continue

      # this block fragment is constrained in a way where it can't be in this group
      if not ilpenv.has_ilpvar(('inst',dblkname,dfragid,grp2)):
        continue

      if not (grp1,grp2) in by_group \
         and grp1 != grp2:
        by_group[(grp1,grp2)] = []


  for cardkey,_ in renv.widths.items():
    (scblkname,sgrp,dcblkname,dgrp) = cardkey
    scblk = board.block(scblkname)
    dcblk = board.block(dcblkname)

    # this block fragment is constrained in a way where it can't be in this group
    if not ilpenv.has_ilpvar(('inst',sblkname,sfragid,sgrp)):
      continue

    # this block fragment is constrained in a way where it can't be in this group
    if not ilpenv.has_ilpvar(('inst',dblkname,dfragid,dgrp)):
      continue

    # the source block does not exist in this group
    if not (sgrp,sblkname) in renv.counts or \
        renv.counts[(sgrp,sblkname)] == 0:
      continue

    # the dest block does not exist in this group
    if not (dgrp,dblkname) in renv.counts or \
        renv.counts[(dgrp,dblkname)] == 0:
      continue

    # the src block cannot be connected to this straddling edge
    if not dcblkname in renv.connectivities[(sblkname,sgrp,sport)]:
      continue

    # the dest block cannot be connect to this straddling edge
    if not scblkname in renv.connectivities[(dblkname,dgrp,dport)]:
      continue


    # this block is a computational block that is not the source block
    if scblk.type != blocklib.BlockType.BUS and \
        scblk.name != sblk.name:
      continue

    # this block is a computational block that is not the dest block
    if dcblk.type != blocklib.BlockType.BUS and \
        dcblk.name != dblk.name:
      continue

    connvar = ilpenv.decl(('conn',conn_id,cardkey),
                          ilpop.ILPEnv.Type.BOOL)

    by_group[(sgrp,dgrp)].append(connvar)

    if not cardkey in by_straddle:
      by_straddle[cardkey] = []

    by_straddle[cardkey].append(connvar)

  idx = 0
  for (g1,g2),data in by_group.items():
    idx += 1

  return by_group

def ilp_connection_cstr(ilpenv,renv):
  by_straddle = {}
  xgroups = []
  board = renv.board
  for conn_id,conn \
      in enumerate(renv.connections):

    by_group = ilp_single_connection_cstr(ilpenv,renv,conn_id,conn, \
                                          by_straddle=by_straddle)
    # add this straddlevar to the list of straddle vars
    ((sblkname,sfragid),sport,(dblkname,dfragid),dport) = conn

    for (sgrp,dgrp),group_conns in by_group.items():
      clause1 = ilpop.ILPAndVar(
        ilpenv,
        ilpop.ILPVar(ilpenv.get_ilpvar(('inst',sblkname,sfragid,sgrp))),
        ilpop.ILPVar(ilpenv.get_ilpvar(('inst',dblkname,dfragid,dgrp)))
      )
      if len(group_conns) > 0:
        xgroup = ilpenv.decl(('xgroup',conn_id,sgrp,dgrp), \
                             ilpop.ILPEnv.Type.BOOL)
        xgroups.append(xgroup)
        ilpenv.eq(
          ilpop.ILPMapAdd(
            list(map(lambda v: ilpop.ILPVar(v), group_conns))
          ),
          ilpop.ILPVar(xgroup)
        )
        ilpenv.eq(
            ilpop.ILPVar(clause1),
            ilpop.ILPVar(xgroup)
        );

      else:
        ilpenv.eq(
            ilpop.ILPVar(clause1),
            ilpop.ILPConst(0)
        )

  for cardkey,variables in by_straddle.items():
    cardinality = len(renv.widths[cardkey])
    ilpenv.lte(
      ilpop.ILPMapAdd(
        list(map(lambda v: ilpop.ILPVar(v), variables))
      ),
      ilpop.ILPConst(cardinality)
    );

  return xgroups

def to_assignments(result):
  config = list(filter(lambda k: result[k] == 1.0, result.keys()))
  n_conns = len(list(filter(lambda k: 'conn' in k, config)))
  print("n_conns: %s" % n_conns)
  assigns = {}
  for key in config:
    if 'inst' in key:
      _,blk,fragid,group = key
      assigns[(blk,fragid)] = group
      print("%s[%s] = %s" % (blk,fragid,group))

  return assigns

def hierarchical_route(board,locs,conns,layers,
                       assigns,
                       groups=None,
                       connection_constraints=True):
  def get_n_conns(result):
    config = list(filter(lambda k: result[k] == 1, result.keys()))
    n_conns = len(list(filter(lambda k: 'conn' in k, config)))
    return n_conns


  print("-> generating environment")
  renv = route_ilp_util.RoutingEnv(board,locs,conns,layers, assigns)
  ilpenv = ilpop.ILPEnv()
  print("-> generating instance constraints")
  ilp_instance_cstr(ilpenv,renv,groups=groups)
  if connection_constraints:
    print("-> generating connection constraints")
    xlayers = ilp_connection_cstr(ilpenv,renv)
    if len(xlayers) > 0:

      ilpenv.set_objfun(
        ilpop.ILPMapAdd(
          list(map(lambda c: ilpop.ILPVar(c), xlayers))
        )
      )
    else:
      ilpenv.set_objfun(ilpop.ILPConst(0))

  else:
    ilpenv.set_objfun(ilpop.ILPConst(0))

  print("-> generate ilp")
  print("# vars: %d" % ilpenv.num_vars())
  print("# tempvars: %d" % ilpenv.num_tempvars())
  print("# cstrs: %d" % ilpenv.num_cstrs())
  subtype = {"inst":0,'conn':0,'xgroup':0}
  conntype = {}
  for var in ilpenv.ilp_vars():
    if var[0] == 'inst':
      subtype['inst'] += 1
    elif var[0] == 'xgroup':
      subtype['xgroup'] += 1
    elif var[0] == 'conn':
      subtype['conn'] += 1
      if not var[2] in conntype:
        conntype[var[2]] = 0
      conntype[var[2]] += 1

  for type_,count in subtype.items():
    print("  # %s vars: %d" % (type_,count))

  ctx = ilpenv.to_model()
  print("-> solve problem")
  results = ctx.solve()
  if not ctx.optimal():
    print("-> FAILED")
    return ilpenv,None

  print("-> SUCCEEDED")
  assigns = to_assignments(results)

  return ilpenv,assigns



def next_solution(ilpenv,assigns):
  terms = []
  for (blk,frag_id),grp in assigns.items():
    instvar = ilpenv.get_ilpvar(('inst',blk,frag_id,grp))
    terms.append(ilpop.ILPEq(ilpop.ILPVar(instvar), \
                             ilpop.ILPConst(1)))


  n = len(terms)
  cstr = ilpop.ILPLTE(ilpop.ILPMapAdd(terms), \
                      ilpop.ILPConst(n-1))
  ilpenv.ctx.cstr(cstr.to_model(ilpenv.ctx))
  result = ilpenv.ctx.solve()
  if not ilpenv.ctx.optimal():
    return ilpenv,None

  assigns = to_assignments(result)
  return ilpenv,assigns




# TODO: check if there exists a path through port before adding to cardinality.

def extract_src_node(fragment,port=None):
    if isinstance(fragment,acirc.ABlockInst):
      assert(not port is None)
      yield fragment,port

    elif isinstance(fragment,acirc.AConn):
      sb,sp = fragment.source
      db,dp = fragment.dest
      for block,port in extract_src_node(sb,port=sp):
        yield block,port

    elif isinstance(fragment,acirc.AInput):
      node,output = fragment.source
      for block,port in extract_src_node(node,port=output):
        yield block,port

    elif isinstance(fragment,acirc.AJoin):
      for ch in fragment.parents():
        for node,port in extract_src_node(ch):
          yield node,port

    else:
        raise Exception(fragment)

def tile_assigns_to_chip_assigns(tile_assigns):
  chip_assigns = {}
  for (block,frag),pos in tile_assigns.items():
    chip_assigns[(block,frag)] = pos[:-1]
  return chip_assigns

def extract_backward_paths(nodes,starting_node):
  conns = []
  for next_node in starting_node.parents():
    if isinstance(next_node,acirc.AConn):
      src_node,src_port_orig = next_node.source
      dest_block,dest_port = next_node.dest
      assert(isinstance(dest_block,acirc.ABlockInst))
      dest_key =(dest_block.block.name, dest_block.id)
      for src_block,src_port in \
          extract_src_node(src_node,port=src_port_orig):
        src_key = (src_block.block.name, src_block.id)
        conns.append((src_key,src_port, \
                      dest_key,dest_port))

  return conns


def route(board,prob,node_map):
  nodes = {}
  for k,v in node_map.items():
    for node in v.nodes():
      if isinstance(node,acirc.ABlockInst):
        key = (node.block.name,node.id)
        assert(not key in nodes)
        nodes[key] = node

  conns = []
  locs = {}
  configs = {}
  for key,node in nodes.items():
    conns += extract_backward_paths(nodes,node)
    locs[key] = node.loc
    configs[key] = node.config

  chips = get_sublayers([board])
  tiles = get_sublayers(chips)


  # build partition tree of tiles
  part_tree = partition_tree.build_partition_tree(board,locs,conns)
  groups = partition_tree.greedy_partition(part_tree,tiles)
  print("=== first map tiles ===")
  # break up into greedily partitioned tiles.
  tile_env,tile_assigns = hierarchical_route(board,locs,conns,
                                             tiles,
                                             assigns={},
                                             groups=groups,
                                             connection_constraints=True)

  success = False
  while not success and not tile_assigns is None:
    success = True
    print("=== route chips ===")
    # convert greedy tile partitions to chip partitions
    chip_assigns = tile_assigns_to_chip_assigns(tile_assigns)
    # try routing with the computed chip assignments
    _,result = hierarchical_route(board,locs,conns,
                                  chips,
                                  chip_assigns,
                                  connection_constraints=True)
    success &= (not result is None)

    if not success:
      # get the next combination of chip assignments
      tile_env,tile_assigns = next_solution(tile_env, \
                                            tile_assigns)


  if not success:
    return None

  for assigns in find_slices.random_locs(board,locs,conns,tile_assigns):
    for routes in find_slices.find_routes(board,locs,conns,assigns):
      ccirc = find_slices.make_concrete_circuit(board, \
                                                routes, \
                                                assigns, \
                                                configs)
      return ccirc
