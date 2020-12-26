import compiler.lgraph_pass.rule as rulelib
import compiler.lgraph_pass.unify as unifylib
import compiler.lgraph_pass.vadp as vadplib
import compiler.lgraph_pass.tableau as tablib
import hwlib.block as blocklib
import ops.generic_op as genoplib
import ops.op as oplib
import ops.opparse as parser

class FlipSignRule(rulelib.Rule):

  def __init__(self):
    rulelib.Rule.__init__(self,"flip")
    self.virt.add_input('a',blocklib.BlockSignalType.ANALOG,  \
                        unifylib.UnifyConstraint.NONE)

    self.virt.set_output(blocklib.BlockSignalType.ANALOG, \
                         unifylib.UnifyConstraint.NONE)
    e = parser.parse_expr('-a')
    self.virt.add_expr("*",e)



  def valid(self,unif):
      print(unif)
      _,expr = unif.get_by_name('a')
      coeff,base = genoplib.factor_coefficient(expr)
      is_variable = (coeff == 1.0 and base.op == oplib.OpType.VAR)
      return is_variable


  def apply(self,goal,rule,unif=None):
    assert(rule.law.name == self.name)
    stmt = []
    if isinstance(goal.variable, tablib.DSVar):
      var_name = goal.variable.var
      mp = tablib.MultiPortVar()
      stmt.append(tablib.VADPSink(mp,goal.expr))
      stmt.append(tablib.VADPSource(goal.var,mp))
    else:
      stmt.append(tablib.VADPSink(goal.variable, goal.expr))

    return unifylib.Unification(),stmt


  def simplify_once(self,vadp):
      return False,vadp
