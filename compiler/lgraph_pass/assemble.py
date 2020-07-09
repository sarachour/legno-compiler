import compiler.lgraph_pass.vadp as vadplib
import hwlib.block as blocklib
import ops.base_op as oplib
import ops.generic_op as genoplib
import itertools

def unzip(lst):
  return list(zip(*lst))

def subset(xs,ys_):
  ys = list(ys_)
  for x in xs:
    if not x in ys:
      return False
    ys.remove(x)

  return True

def powerset(iterable):
    """
    powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)
    """
    xs = list(iterable)
    # note we return an iterator rather than a list
    return itertools.chain.from_iterable( \
                                          itertools.combinations(xs,n)  \
                                          for n in range(len(xs)+1))


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

# configure the asm blk to accept `input_var` and generate `sinks`
def build_asm(blk,ident,input_var,sinks):
  if len(sinks) < 2:
    return

  target = sinks[0]
  assert(len(blk.inputs) == 1)
  input_port = list(blk.inputs)[0].name
  rel_opts = {}
  for output in blk.outputs:
    rel_opts[output.name] = []
    for expr,modes in output.relation.get_by_property():
      conc_rel = expr.substitute({ \
                        input_port:genoplib.Var(input_var) \
      })
      rel_opts[output.name].append((modes,conc_rel))

  output_ports = list(rel_opts.keys())
  output_values = list(map(lambda p: rel_opts[p], \
                            output_ports))
  for combo in itertools.product(*output_values):
    modes,exprs, = unzip(combo)
    isect_modes = set.intersection(*map(lambda m: set(m), \
                                        modes))
    if len(isect_modes) == 0:
      continue

    if not subset(sinks,exprs):
      continue

    vadpprog = []
    vadpprog.append(vadplib.VADPConfig(blk,ident, \
                                list(isect_modes)))

    port_var = vadplib.PortVar(blk,ident,list(blk.inputs)[0])
    vadpprog.append(vadplib.VADPSink(port_var, \
                                    genoplib.Var(input_var)))
    for outp,expr in zip(output_ports,exprs):
      port_var = vadplib.PortVar(blk,ident,blk.outputs[outp])
      vadpprog.append(vadplib.VADPSource(port_var, \
                                  expr))
    yield vadpprog


def all_subsets(lst,subset_sizes):
  indices = list(range(0,len(lst)))
  if len(lst) == 0 and len(subset_sizes) == 0:
    yield []
    return
  elif len(subset_sizes) == 0 or len(lst) == 0:
    return

  any_size = subset_sizes[0] is None
  if any_size:
    enumerator = powerset(indices)
  else:
    enumerator = itertools.combinations(indices,subset_sizes[0])

  for subindices in enumerator:
    # make sure that we're actually reducing the complexity
    if any_size and len(subindices) <= 1:
      continue

    next_lst = list(map(lambda i: lst[i], \
                        filter(lambda i: not i in subindices, \
                               indices)));
    this_lst = list(map(lambda i: lst[i], subindices))
    for subsets in all_subsets(next_lst,subset_sizes[1:]):
      yield [this_lst]+subsets

def assemble_asms(root_vadp,vadps):
  sinks = {}
  sources = {}
  assembled_vadp = []

  # find which signals are being generated
  for stmt in root_vadp:
    if isinstance(stmt,vadplib.VADPSource):
      if not stmt.dsexpr in sources:
        sources[stmt.dsexpr] = []
        sinks[stmt.dsexpr] = []

      sources[stmt.dsexpr].append(stmt.port)
    else:
      assembled_vadp.append(stmt)

  # figure out which signals are needed by the circuits
  for stmt in vadps:
    if isinstance(stmt,vadplib.VADPSink):
      if stmt.dsexpr in sources:
        sinks[stmt.dsexpr].append(stmt.port)
      else:
        assembled_vadp.append(stmt)
    else:
      assembled_vadp.append(stmt)

  # link together the sinks and sources
  for dsexpr in sources:
    assert(len(sources[dsexpr]) >= len(sinks[dsexpr]))
    for idx,source in enumerate(sources[dsexpr]):
      if idx < len(sinks[dsexpr]):
        assembled_vadp.append(vadplib.VADPConn(source,sinks[dsexpr][idx]))
      else:
        assembled_vadp.append(vadplib.VADPSource(source,dsexpr))


  return assembled_vadp

# build a nested  hierarchy of asms
def build_asm_frag(asm_blocks,input_var,sinks):
  n_asm_fragments=10
  n_generated = 0
  indices = list(range(0,len(sinks)))
  if len(sinks) <= 1:
    yield []
    return

  for blk in asm_blocks:
    if len(sinks) > len(blk.outputs):
      # chain one asm in series
      n_outputs = len(blk.outputs)
      for n_child_asms in range(1,n_outputs+1):
        subsets = [n_outputs-n_child_asms] \
                  + [None]*n_child_asms
        for sink_subsets in all_subsets(sinks, \
                                        subsets):
          child_frags = [None]*(n_child_asms)
          for idx,sink_subset in enumerate(sink_subsets[1:]):
            child_frags[idx] = list(get_first_n(build_asm_frag(asm_blocks, \
                                                                  input_var, \
                                                                  sink_subset),
                                                n_asm_fragments))

          for children in itertools.product(*child_frags):
            first_subset = [genoplib.Var(input_var)]*n_child_asms \
                           + sink_subsets[0];
            for root_node in build_asm_frag(asm_blocks, \
                                               input_var, \
                                               first_subset):
              block_counts = {}
              root_vadp = remap_vadps([root_node],block_counts)
              vadps = remap_vadps(list(children),block_counts)
              yield assemble_asms(root_vadp,vadps)

    elif len(sinks) > 1:
      for frag in build_asm(blk,0,input_var,sinks):
        yield frag

    else:
      raise Exception("not possible: %d sinks" % (len(sinks)))

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

    assert(len(sink_ports) <= len(source_ports))
    for srcs,sink in zip(source_ports,sink_ports):
      for src in srcs:
        assembled.append(vadplib.VADPConn(src,sink))

  return assembled

def assemble(blocks,fragments,depth=3):

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


  # build asms
  asm_frags = {}
  for var,sinks in sinks.items():
    asm_frags[var] = []
    for frag in build_asm_frag(blocks, \
                                  var, \
                                  sinks):
      asm_frags[var].append(frag)


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
    yield circ
