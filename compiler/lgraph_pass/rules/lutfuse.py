import compiler.lgraph_pass.rule as rulelib
import compiler.lgraph_pass.unify as unifylib
import compiler.lgraph_pass.vadp as vadplib
import compiler.lgraph_pass.tableau as tablib
import hwlib.block as blocklib
import ops.generic_op as genoplib
import ops.opparse as parser

class FuseLUTRule(rulelib.Rule):

  def __init__(self,dev):
    rulelib.Rule.__init__(self,"lutfuse")
    self.dev = dev

    self.virt.add_input('a',blocklib.BlockSignalType.ANALOG,  \
                        unifylib.UnifyConstraint.NONE)


    self.virt.add_data('e',blocklib.BlockSignalType.DIGITAL,  \
                       unifylib.UnifyConstraint.NONE)

    self.virt.set_output(blocklib.BlockSignalType.ANALOG, \
                         unifylib.UnifyConstraint.NONE)

    fxns = {'f':(['y'],parser.parse_expr('e'))}
    e = parser.parse_expr('2.0*f((0.5*a))', fxns)
    self.virt.add_expr(('m','m'), e)

    e = parser.parse_expr('2.0*f((0.05*a))', fxns)
    self.virt.add_expr(('h','m'), e)

    e = parser.parse_expr('20.0*f((0.05*a))', fxns)
    self.virt.add_expr(('h','h'), e)

    e = parser.parse_expr('20.0*f((0.5*a))', fxns)
    self.virt.add_expr(('m','h'), e)


  def apply(self,goal,rule,unif=None):
    assert(not unif is None)
    assert(rule.law.name == self.name)

    law_var = tablib.LawVar(self.name,rule.target.ident)
    out_var = law_var.make_law_var(self.virt.output.name)
    stmts = []
    if isinstance(goal.variable, tablib.DSVar):
      var_name = goal.variable.var
      stmts.append(tablib.VADPSource(out_var,genoplib.Var(var_name)))
    else:
      stmts.append(tablib.VADPConn(out_var,goal.variable))

    _,inpexpr = unif.get_by_name('a')
    coeff,base_expr = genoplib.factor_coefficient(inpexpr)
    assert(not base_expr is None)
    _,expr = unif.get_by_name('e')
    repl = {'T': genoplib.Mult(genoplib.Const(1.0/coeff),  \
                               genoplib.Var("y")) \
    }
    cfg = tablib.VADPConfig(law_var,rule.mode)
    cfg.bind('e',expr.substitute(repl))
    stmts.append(cfg)

    new_unif = unifylib.Unification()
    new_unif.set_by_name('a', base_expr)
    return new_unif,stmts


  def simplify_once(self,vadp):
    target_stmt = None
    for stmt in filter(lambda stmt: not self.get_usage(stmt) is None, vadp):
      if isinstance(stmt,tablib.VADPConfig):
        target_stmt = stmt
        break

    if target_stmt is None:
      return False,vadp

    lawvar = self.get_law_var(target_stmt)
    new_vadp = []
    dev = self.dev
    identifier = lawvar.ident
    mode = target_stmt.mode
    lut = vadplib.PortVar(dev.get_block('lut'),identifier)
    lut_mode = lut.block.modes[["*"]]
    assert(isinstance(lut_mode,blocklib.BlockMode))
    lut_cfg = vadplib.VADPConfig(lut,[lut_mode])
    lut_cfg.bind('e', target_stmt.assigns['e'])
    new_vadp.append(lut_cfg)

    adc = vadplib.PortVar(dev.get_block('adc'),identifier)
    adc_mode = adc.block.modes[["m"] if mode[1] == "m" else ["h"]]
    assert(isinstance(adc_mode,blocklib.BlockMode))
    adc_cfg = vadplib.VADPConfig(adc,[adc_mode])
    new_vadp.append(adc_cfg)

    dac = vadplib.PortVar(dev.get_block('dac'),identifier)
    dac_mode = dac.block.modes[["dyn","m"] if mode[1] == "m" else ["dyn","h"]]
    assert(isinstance(dac_mode,blocklib.BlockMode))
    dac_cfg = vadplib.VADPConfig(dac,[dac_mode])
    new_vadp.append(dac_cfg)

    new_vadp.append(vadplib.VADPConn(adc.make_port_var('z'), \
                                     lut.make_port_var('x')))

    new_vadp.append(vadplib.VADPConn(lut.make_port_var('z'), \
                                     dac.make_port_var('x')))


    for stmt in vadp:
      if self.is_same_usage(stmt,lawvar):
        usage = self.get_usage(stmt)
        if usage == rulelib.Rule.Usage.VADP_CONN_SOURCE:
          new_vadp.append(vadplib.VADPConn(dac.make_port_var('z'), \
                                           stmt.sink))
        elif usage == rulelib.Rule.Usage.VADP_CONN_SINK:
          new_vadp.append(vadplib.VADPConn(stmt.source, \
                                       adc.make_port_var('x')))
        elif usage == rulelib.Rule.Usage.VADP_SOURCE:
          new_vadp.append(vadplib.VADPSource(dac.make_port_var('z'), \
                                             stmt.dsexpr))
        elif usage == rulelib.Rule.Usage.VADP_SINK:
          new_vadp.append(vadplib.VADPSink(adc.make_port_var('x'), \
                                           stmt.dsexpr))
        elif usage == rulelib.Rule.Usage.VADP_CONFIG:
          pass
        else:
          raise Exception("???")
      else:
        new_vadp.append(stmt)

    return True,new_vadp
