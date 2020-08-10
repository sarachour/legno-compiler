import compiler.lgraph_pass.vadp as vadplib
import compiler.lgraph_pass.vadp_renderer as vadp_renderer
import hwlib.block as blocklib
import ops.base_op as oplib
import ops.generic_op as genoplib
import itertools
import numpy as np

def unzip(lst):
  return list(zip(*lst))

def get_first_n(iterable,n):
  for idx,val in enumerate(iterable):
    if idx < n:
      yield val
    else:
      return

def get_vadp_source(stmts,variable):
  for stmt in stmts:
    if isinstance(stmt,VADPSource):
      if stmt.dsexpr == genoplib.Var(variable):
        return stmt.port

def group_mode_sets(blk,input_var):
  groupby_mode = {}
  inp = list(blk.inputs)[0]
  output_names = list(map(lambda o: o.name, blk.outputs))
  for mode in blk.modes:
    key = ""
    for output in output_names:
      rel = blk.outputs[output] \
               .relation[mode].substitute({inp.name:genoplib.Var(input_var)})
      key += "%s=%s," % (output,rel)
    if not key in groupby_mode:
      groupby_mode[key] = []
    groupby_mode[key].append(mode)
  return groupby_mode.values()

def build_fragment_corpus(asm_blocks,input_var):
  fragment_map = []
  for blk in asm_blocks:
    assert(len(blk.inputs) == 1)
    inp = list(blk.inputs)[0]
    modeset_groups = group_mode_sets(blk,input_var)
    for modeset in modeset_groups:
      leaves = {}
      stems = []
      for output in blk.outputs:
        rel = output.relation[modeset[0]] \
                    .substitute({inp.name:genoplib.Var(input_var)})
        if rel.op == oplib.OpType.VAR and rel.name == input_var:
          stems.append(output.name)

        leaves[output.name] = rel
      fragment_map.append({
        'block':blk,
        'modes':modeset,
        'exprs':leaves,
        'stems':stems
      })

  return fragment_map

def find_best_assembly_set(corpus,sinks):
  def get_best_stem(ports_in_use,scores,best_score):
    # get fragment that resolves most sinks and has most stems
    best_entry = -1
    max_n_stems = -1
    for idx,score in enumerate(scores):
      if score == best_score:
        stems = list(set(corpus[idx]['stems']) \
                    .difference(set(ports_in_use[idx])))
        if len(stems) > max_n_stems:
          max_n_stems = len(stems)
          best_entry = idx
    return best_entry

  scores = [0]*len(corpus)
  new_sinks = [None]*len(corpus)
  ports_in_use = [None]*len(corpus)
  if len(sinks) == 0:
    yield []
    return

  for entry_idx,entry in enumerate(corpus):
    new_sinks[entry_idx]= list(map(lambda s : str(s), sinks))
    ports_in_use[entry_idx] = []
    for port,ent in  entry['exprs'].items():
      if str(ent) in new_sinks[entry_idx]:
        idx = new_sinks[entry_idx].index(str(ent))
        new_sinks[entry_idx].pop(idx)
        ports_in_use[entry_idx].append(port)

    scores[entry_idx] = len(sinks) - len(new_sinks[entry_idx])
  # iterate over options, starting from fragment that solves most 
  while max(scores) > 0:
    max_score = max(scores)
    best_entry = get_best_stem(ports_in_use,scores,max_score)
    new_sink_list = new_sinks[best_entry]
    new_frag = dict(corpus[best_entry])
    new_frag['stems'] = list(set(new_frag['stems']) \
                            .difference(set(ports_in_use[best_entry])))

    for other_frags in find_best_assembly_set(corpus,new_sink_list):
      yield [new_frag] + other_frags

    for idx in range(len(scores)):
      if scores[idx] == max_score:
        scores[idx] = -1

def build_frag_hierarchy(frag_list,parent=None):

  new_frag_list = list(frag_list)
  if parent is None:
    best_idx = np.argmax(list(map(lambda frag: len(frag['stems']), frag_list)))
  else:
    best_idx=frag_list.index(parent)

  # remove best index from new fragment list
  new_frag_list.pop(best_idx)
  hierarchy = [[]]
  hierarchy[0] = [frag_list[best_idx]]
  # if the root node cannot feed any more assembly blocks, or there are no more leftovers
  if len(hierarchy[0][0]['stems']) == 0 or len(new_frag_list) == 0:
    assert(len(hierarchy[0]) > 0)
    return hierarchy,new_frag_list

  hierarchy.append([])
  for _ in range(len(frag_list[best_idx]['stems'])):
    # we exhausted the number of fragments
    if len(new_frag_list) == 0:
      break

    # choose the child with the most active stems
    best_child_idx = np.argmax(list(map(lambda frag: len(frag['stems']), \
                                        new_frag_list)))
    hierarchy[1].append(new_frag_list[best_child_idx])
    new_frag_list.pop(best_child_idx)

  leftover = new_frag_list
  if len(leftover) == 0:
    assert(len(hierarchy[0]) > 0 and len(hierarchy[1]) > 0)
    return hierarchy,[]
  else:
    for frag in hierarchy[1]:
      sub_hierarchy,new_leftover = build_frag_hierarchy(list(leftover)+[frag],parent=frag)
      # extend the hierarchy
      for hierarchy_level,blocks in enumerate(sub_hierarchy[1:]):
        if len(blocks) == 0:
          continue
        if hierarchy_level+1 >= len(hierarchy):
          hierarchy.append([])
        for block in blocks:
          hierarchy[hierarchy_level+1].append(block)
      leftover = new_leftover

    for lvl in hierarchy:
      assert(len(lvl) > 0)

    return hierarchy,leftover



def build_asm_frag(corpus,input_var,sinks):
  if len(sinks) <= 1:
    yield []
    return

  for frag_list in find_best_assembly_set(corpus,sinks):
    # count how many sources of input_var we need
    n_sinks = len(frag_list)
    # count how many propagated signals of input_var are produced by fragments
    n_stems = sum(map(lambda frag: len(frag['stems']), frag_list))
    if n_stems > 0:
      frag_hierarchy,leftover = build_frag_hierarchy(frag_list)
      frag_hierarchy[0] += leftover
      n_stems_required = len(leftover)+1
    else:
      frag_hierarchy = [frag_list] if len(frag_list) > 0 else []
      n_stems_required = len(frag_list)
    # if we only need one stem, we're done.
    if n_stems_required <= 1:
      yield frag_hierarchy
      return

    # produce new set of sinks to fulfill
    new_sinks = list(map(lambda idx : genoplib.Var(input_var), \
                        range(n_stems_required)))

    for par_frags in build_asm_frag(corpus,input_var,new_sinks):
      new_frags = list(map(lambda lv: [], range(len(par_frags) + len(frag_hierarchy))))
      for hierarchy_level,blocks in enumerate(par_frags):
        new_frags[hierarchy_level] = list(blocks)
        assert(len(list(blocks)) > 0)

      for hierarchy_level,blocks in enumerate(frag_hierarchy):
        lv = hierarchy_level + len(par_frags)
        new_frags[lv] = list(blocks)
        assert(len(list(blocks)) > 0)

      yield new_frags


def assemble_circuit(stmts):
  def add(dict_,key,val):
    if not key in dict_:
      dict_[key] = []
    dict_[key].append(val)

  asm_sinks = {}
  compute_sinks = {}
  asm_sources = {}
  compute_sources= {}
  assembled = []
  for stmt in stmts:
    if isinstance(stmt,vadplib.VADPSink):
      if stmt.port.block.type == blocklib.BlockType.ASSEMBLE:
        add(asm_sinks,stmt.dsexpr,stmt.port)
      else:
        add(compute_sinks,stmt.dsexpr,stmt.port)

    elif isinstance(stmt,vadplib.VADPSource):
      if isinstance(stmt.port,vadplib.VirtualSourceVar):
        srcs = vadplib.get_virtual_variable_sources(stmts,stmt.port)
        add(compute_sources,stmt.dsexpr, srcs)
        continue
      elif stmt.port.block.type == blocklib.BlockType.ASSEMBLE:
        add(asm_sources,stmt.dsexpr,[stmt.port])
      else:
        add(compute_sources,stmt.dsexpr,[stmt.port])

      assembled.append(stmt)

    elif isinstance(stmt,vadplib.VADPConn):
      if not isinstance(stmt.sink,vadplib.VirtualSourceVar):
        assembled.append(stmt)

    else:
      assembled.append(stmt)


  for dsexpr,sink_ports in asm_sinks.items():
    source_ports = compute_sources[dsexpr]
    assert(len(sink_ports) <= len(source_ports))
    assert(len(source_ports) == 1)
    for srcs,sink in zip(source_ports,sink_ports):
      for src in srcs:
        assembled.append(vadplib.VADPConn(src,sink))

    compute_sources[dsexpr] = []

  for dsexpr,sink_ports in compute_sinks.items():
    source_ports = compute_sources[dsexpr]
    if dsexpr in asm_sources:
      source_ports += asm_sources[dsexpr]

    print(dsexpr,len(sink_ports),len(source_ports))
    assert(len(sink_ports) <= len(source_ports))
    for srcs,sink in zip(source_ports,sink_ports):
      for src in srcs:
        assembled.append(vadplib.VADPConn(src,sink))

  return assembled

def create_vadp_frag(hierarchy,input_var,parent_vadp,instance_map={}):
  def fresh_ident(block):
    if not block.name in instance_map:
      instance_map[block.name] = 0
    inst = instance_map[block.name]
    instance_map[block.name] += 1
    return inst

  if len(hierarchy) == 0:
    return []

  vadp = []
  n_children = len(hierarchy[1]) if len(hierarchy) > 1 else 0
  stems = []
  for frag in hierarchy[0]:
    inst = fresh_ident(frag['block'])
    vadp.append(vadplib.VADPConfig(frag['block'],inst,frag['modes']))
    inp_port = vadplib.PortVar(frag['block'],inst, \
                               list(frag['block'].inputs)[0])
 
    for port,expr in frag['exprs'].items():
      out_port_var = vadplib.PortVar(frag['block'],inst,frag['block'].outputs[port])
      vadp.append(vadplib.VADPSource(out_port_var,expr))

    # inject connection
    found_source = False
    for idx,stmt in enumerate(parent_vadp):
      if isinstance(stmt,vadplib.VADPSource) and stmt.dsexpr.op == oplib.OpType.VAR \
         and stmt.dsexpr.name == input_var:
        vadp.append(vadplib.VADPConn(stmt.port, inp_port))
        parent_vadp.pop(idx)
        found_source = True
        break
    if not found_source:
      vadp.append(vadplib.VADPSink(inp_port, genoplib.Var(input_var)))

  enclosing_vadp = list(vadp) + list(parent_vadp)
  if len(hierarchy) > 1:
    vadp += create_vadp_frag(hierarchy[1:],input_var,enclosing_vadp,instance_map)

  # at most one sink statement
  sources = list(filter(lambda vst: isinstance(vst,vadplib.VADPSource), vadp))
  other_stmts = list(filter(lambda vst: not isinstance(vst,vadplib.VADPSource), vadp))
  for st in vadp:
    if isinstance(st,vadplib.VADPConn):
      sources = list(filter(lambda src: st.source != src.port,sources))

  vadp = sources + other_stmts
  n_sinks = len(list(filter(lambda vst: isinstance(vst,vadplib.VADPSink), vadp)))
  assert(n_sinks <= 1)
  return vadp

def assemble(blocks,fragments,n_asm_frags=3):

  # count sinks and sources
  sources = {}
  sinks = dict(map(lambda var: (var,[]), \
                   fragments.keys()))
  for var,frag in fragments.items():
    for stmt in frag:
      if isinstance(stmt,vadplib.VADPSink):
        assert(len(stmt.dsexpr.vars()) == 1)
        variable = stmt.dsexpr.vars()[0]
        sinks[variable].append(stmt.dsexpr)
      if isinstance(stmt,vadplib.VADPSource):
        assert(not var in sources)
        sources[var] = stmt.dsexpr


  # build assemble fragments
  asm_frags = {}
  for var,sinks in sinks.items():
    asm_frags[var] = []
    for frag in get_first_n(build_asm_frag(build_fragment_corpus(blocks,var), \
                                           var, sinks), n_asm_frags):

      vadp_frag = create_vadp_frag(frag,var,[])
      asm_frags[var].append(vadp_frag)

  asm_frag_vars = list(asm_frags.keys())
  asm_frag_values = list(map(lambda var: asm_frags[var], \
                                asm_frag_vars))

  for combo in itertools.product(*asm_frag_values):
    disconn_circuit = vadplib.remap_vadps(list(fragments.values()) \
                                         + list(combo))
    circ = assemble_circuit(disconn_circuit)
    if not vadplib.is_concrete_vadp(circ):
      for stmt in circ:
        print(stmt)
      raise Exception("vadp is not concrete")


    vadp_renderer.render(circ,'asm')
    yield circ
