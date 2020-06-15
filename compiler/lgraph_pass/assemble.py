from compiler.lgraph_pass.tableau_data import *
import compiler.lgraph_pass.tableau as tablib
import compiler.lgraph_pass.unify as unifylib
import ops.base_op as oplib
import ops.generic_op as genoplib

class UnificationTable:
  class Entry:

    def __init__(self,block,port,modes,expr,target_expr,in_expr):
      self.block = block
      self.port = port
      self.modes = modes
      self.port_expr = expr
      self.target_expr = target_expr
      self.in_expr = in_expr

    def __repr__(self):
      s = "%s.%s" % (self.block.name,self.port.name)
      s += " #modes=%d" % len(self.modes)
      s += ": port=%s, targ=%s, inp=%s" % (self.port_expr, \
                                           self.target_expr, \
                                           self.in_expr)
      return s

  def __init__(self):
    self.sources = []
    self.source_ports = []
    self.sinks = []
    self.sink_ports = []
    self.by_sink = {}
    self.by_source = {}


  def add(self,e):
    if not e.target_expr in self.by_sink:
      self.by_sink[e.target_expr] = []

    if not e.in_expr in self.by_source:
      self.by_source[e.in_expr] = []

    self.by_sink[e.target_expr].append(e)
    self.by_source[e.in_expr].append(e)

def valid_unification(table,unif):
  for var,expr in unif.assignments:
    if not expr in table.sources:
      return False
  return True

def unification_to_config(block,unif):
  in_expr = None
  for v,e in unif.assignments:
    assert(v.op == oplib.OpType.VAR)
    assert(len(block.inputs) == 1)
    if not block.inputs.has(v.name):
      raise Exception("only input assignments allowed: %s" % v.name)

    in_expr = e

  assert(not in_expr is None)
  return in_expr

def make_unification_table(blocks,fragments):
  table = UnificationTable()
  for variable in fragments.keys():
    for stmt in fragments[variable]:
      if isinstance(stmt,VADPSink):
        table.sinks.append(stmt.dsexpr)
        table.sink_ports.append(stmt.port)

      elif isinstance(stmt,VADPSource):
        table.sources.append(stmt.dsexpr)
        table.source_ports.append(stmt.port)

  for block in blocks:
    for output in block.outputs:
      for expr,modes in output.relation.get_by_property():
        cstrs = dict(map(lambda v: (v,unifylib.UnifyConstraint.NONE), \
                    expr.vars()))

        for target in set(table.sinks + table.sources):
          for unif in unifylib.unify(expr,target,cstrs):
            if valid_unification(table,unif):
              entry = UnificationTable.Entry(block,output,modes, \
                                            expr,target, \
                                            unification_to_config(block, \
                                                                  unif))
              table.add(entry)

    return table

def build_copiers(table,insts,source):
  def get_identifier(instmap,blk):
    if not blk.name in instmap:
      instmap[blk.name] = 0
    else:
      instmap[blk.name] += 1
    return instmap[blk.name]

  new_table = table
  for i,target_sink in enumerate(table.sinks):
    for entry in table.by_source[source]:
      if entry.target_expr in table.sinks:
        continue

      ident = get_identifier(insts,entry.block)
      cfg = VADPConfig(entry.block,ident,entry.modes)
      print(entry)
  input()

def assemble(blocks,fragments,depth=3):
  table = make_unification_table(blocks,fragments)
  all_stmts = []

  # each source is unique.
  for var,frag in fragments.items():
    sources = list(filter(lambda e: var in e.vars(),table.sources))
    assert(len(sources) == 1)
    build_copiers(table,{},sources[0])
  raise NotImplementedError
