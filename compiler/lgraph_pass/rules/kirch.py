import compiler.lgraph_pass.rule as rulelib
import compiler.lgraph_pass.unify as unifylib
import compiler.lgraph_pass.vadp as vadplib
import compiler.lgraph_pass.tableau as tablib
import hwlib.block as blocklib
import ops.generic_op as genoplib
import ops.op as oplib
import ops.opparse as parser

class KirchhoffRule(rulelib.Rule):

  def __init__(self):
    rulelib.Rule.__init__(self,"kirch")
    self.virt.add_input('a',blocklib.BlockSignalType.ANALOG,  \
                        unifylib.UnifyConstraint.NONE)

    self.virt.add_input('b',blocklib.BlockSignalType.ANALOG, \
                        unifylib.UnifyConstraint.NONE)
    self.virt.set_output(blocklib.BlockSignalType.ANALOG, \
                         unifylib.UnifyConstraint.NONE)
    e = parser.parse_expr('a+b')
    self.virt.add_expr("*",e)



  def valid(self,unif):
    for var,val in unif.assignments:
      if val.op == oplib.OpType.CONST and \
         val.value == 0.0:
        return False

    return True

  def apply(self,goal,rule,unif=None):
    assert(rule.law.name == self.name)
    law_var = rule.target.make_law_var(self.virt.output.name)
    stmt = []
    if isinstance(goal.variable, tablib.DSVar):
      var_name = goal.variable.var
      stmt.append(tablib.VADPSource(law_var,genoplib.Var(var_name)))
    else:
      stmt.append(tablib.VADPConn(law_var,goal.variable))

    return unif,stmt


  def simplify_once(self,vadp):
    target = None
    for stmt in filter(lambda stmt: not self.get_usage(stmt) is None, vadp):
      target = stmt
      break

    if target is None:
      return False,vadp

    lawvar = self.get_law_var(target)
    sources = []
    sink = None
    new_vadp = []
    source_dsexprs = []
    sink_dsexprs = []
    for st in vadp:
      if self.is_same_usage(st,lawvar):
        usage = self.get_usage(st,target=lawvar)
        if usage == rulelib.Rule.Usage.VADP_CONN_SINK:
          sources.append(st.source)

        elif usage == rulelib.Rule.Usage.VADP_CONN_SOURCE:
          assert(sink is None)
          sink = st.sink

        elif usage == rulelib.Rule.Usage.VADP_SOURCE:
          source_dsexprs.append(st.dsexpr)
          assert(sink is None)
          sink = tablib.MultiPortVar()

        elif usage == rulelib.Rule.Usage.VADP_SINK:
          sink_dsexprs.append(st.dsexpr)
        else:
          raise Exception("unhandled: %s" % st)
      else:
        new_vadp.append(st)

    assert(not sink is None)
    for src in sources:
      new_vadp.append(tablib.VADPConn(src,sink))

    for dsexpr in source_dsexprs:
      new_vadp.append(tablib.VADPSource(sink,dsexpr))

    for dsexpr in sink_dsexprs:
      new_vadp.append(tablib.VADPSink(sink,dsexpr))


    return True,new_vadp
