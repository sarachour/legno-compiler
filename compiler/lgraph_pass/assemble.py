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
      self.expr = expr
      self.target = target_expr
      self.in_expr = in_expr

  def __init__(self):
    self.sources = []
    self.sinks = []
    self.by_sink = {}
    self.by_source = {}


  def add(self,e):
    if not e.target in self.by_sink:
      self.by_sink[e.target] = []

    if not e.target in self.by_source:
      self.by_source[e.in_expr] = []

    self.by_sink[e.target].append(e)
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

      elif isinstance(stmt,VADPSource):
        table.sources.append(stmt.dsexpr)

  for block in blocks:
    for output in block.outputs:
      for expr,modes in output.relation.get_by_property():
        cstrs = dict(map(lambda v: (v,unifylib.UnifyConstraint.NONE), \
                    expr.vars()))

        for target in table.sinks + table.sources:
          for unif in unifylib.unify(expr,target,cstrs):
            if valid_unification(table,unif):
              entry = UnificationTable.Entry(block,output,modes, \
                                            expr,target, \
                                            unification_to_config(block, \
                                                                  unif))
              table.add(entry)

    return table

def assemble(blocks,fragments,depth=20):
  table = make_unification_table(blocks,fragments)

  for var,frag in fragments.items():
    source = list(filter(lambda e: var in e.vars(),table.sources))[0]
    print("(%s) %s: " % (var,source))
    print(frag)
  raise NotImplementedError
