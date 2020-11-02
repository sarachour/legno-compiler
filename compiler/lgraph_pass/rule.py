import compiler.lgraph_pass.unify as unifylib
import compiler.lgraph_pass.vadp as vadplib
import compiler.lgraph_pass.tableau as tablib
import ops.generic_op as genoplib
from enum import Enum

class Rule:
  APP = "app"

  class Usage(Enum):
    VADP_CONN_SOURCE ="connsrc"
    VADP_CONN_SINK ="connsink"
    VADP_CONFIG = "cfg"
    VADP_SINK = "sink"
    VADP_SOURCE = "source"

  class VirtualBlock:

    class Variable:

      def __init__(self,name,typ,unif_cstr):
        self.unify_cstr = unif_cstr
        self.sigtype = typ
        self.name = name

    def __init__(self):
      self.exprs = {}
      self.inputs = {}
      self.data = {}
      self.output = None

    @property
    def relations(self):
      for mode,expr in self.exprs.items():
        yield mode,expr

    def get_variable(self,name):
      if name in self.inputs:
        return self.inputs[name]
      if name in self.data:
        return self.data[name]
      if name == self.output.name:
        return self.output
      raise Exception("unknown variable <%s>" % name)

    def get_type(self,varname):
      assert(isinstance(varname,str))
      var = self.get_variable(varname)
      return var.sigtype

    def typecheck(self,typ):
      return self.output.sigtype == typ

    def unify_cstrs(self):
      cstrs = {}
      for vport in self.inputs.values():
        cstrs[vport.name] = vport.unify_cstr
      for vport in self.data.values():
        cstrs[vport.name] = vport.unify_cstr
      cstrs[self.output.name] = self.output.unify_cstr
      return cstrs

    def set_output(self,typ,unifyrule):
      self.output = Rule.VirtualBlock.Variable(Rule.APP,typ,unifyrule)

    def add_data(self,name,typ,unifyrule):
      self.data[name] = Rule.VirtualBlock.Variable(name,typ,unifyrule)


    def add_input(self,name,typ,unifyrule):
      self.inputs[name] = Rule.VirtualBlock.Variable(name,typ,unifyrule)

    def add_expr(self,mode,expr):
      self.exprs[mode] = expr


  def __init__(self,name):
    self.name = name
    self.virt = Rule.VirtualBlock()


  def simplify(self,vadp):
    applied = True
    while applied:
      applied,vadp = self.simplify_once(vadp)
    return vadp


  def get_usage(self,stmt,target=None):
    if isinstance(stmt, tablib.VADPConn) and \
       isinstance(stmt.source, tablib.LawVar) and \
       stmt.source.law == self.name and \
       (target is None or target.same_usage(stmt.source)):
      return Rule.Usage.VADP_CONN_SOURCE

    elif isinstance(stmt, tablib.VADPConn) and \
         isinstance(stmt.sink, tablib.LawVar) and \
         stmt.sink.law == self.name and \
         (target is None or target.same_usage(stmt.sink)):
      return Rule.Usage.VADP_CONN_SINK

    elif isinstance(stmt,tablib.VADPConfig) and \
         isinstance(stmt.target, tablib.LawVar) and \
         stmt.target.law == self.name:
      return Rule.Usage.VADP_CONFIG

    elif isinstance(stmt,tablib.VADPSource) and \
         isinstance(stmt.target, tablib.LawVar) and \
         stmt.target.law == self.name and \
         (target is None or target.same_usage(stmt.target)):
      return Rule.Usage.VADP_SOURCE

    elif isinstance(stmt,tablib.VADPSink) and \
         isinstance(stmt.target, tablib.LawVar) and \
         stmt.target.law == self.name and \
         (target is None or target.same_usage(stmt.target)):
      return Rule.Usage.VADP_SINK

    return None

  def is_same_usage(self,vadpst,rulevar):
    usage = self.get_usage(vadpst,rulevar)
    return not usage is None

  def get_law_var(self,vadpst):
    usage = self.get_usage(vadpst)
    if usage is None:
      return None
    if usage == Rule.Usage.VADP_CONN_SOURCE:
      return vadpst.source
    elif usage == Rule.Usage.VADP_CONN_SINK:
      return vadpst.sink
    else:
      return vadpst.target




def cstrs_flip(variables):
  cstrs = dict(map(lambda v: (v,unifylib.UnifyConstraint.VARIABLE), \
                         variables))
  return cstrs

def apply_flip(goal,rule,unif):
  law_var = tablib.LawVar(rule.law,rule.ident,tablib.LawVar.APPLY)
  if isinstance(goal.variable, tablib.PortVar):
    yield tablib.VADPConn(law_var, goal.variable)

  elif isinstance(goal.variable, tablib.DSVar):
    return

def simplify_flip(dev,vadp_stmts,rule):
  sink_stmt = None
  for stmt in vadp_stmts:
    # identify a connection or source flip is used
    if isinstance(stmt, tablib.VADPConn) and \
       isinstance(stmt.source, tablib.LawVar) and \
       stmt.source.law == rule.law:
      sink_stmt = stmt
      sink_var = stmt.sink
      target_var = stmt.source
      break
    elif isinstance(stmt,tablib.VADPSource) and \
         isinstance(stmt.target, tablib.LawVar) and \
         stmt.target.law == rule.law:
      sink_stmt = stmt
      sink_var = VirtualSourceVar(stmt.dsexpr.name)
      target_var = stmt.port
      break

  # is there is no statement with rule variables
  if sink_stmt is None:
    return False,vadp_stmts

  # identify sink statement connected to law variable
  new_stmt = []
  replaced_stmts = [sink_stmt]
  for stmt in vadp_stmts:
    if isinstance(stmt,tablib.VADPSink) and \
       isinstance(stmt.port, tablib.LawVar) and \
       stmt.port.same_usage(target_var):
      new_stmt.append(tablib.VADPSink(sink_var, \
                               genoplib.Mult(genoplib.Const(-1), \
                                             stmt.dsexpr) \
      ))
      replaced_stmts.append(stmt)

  new_vadp = []
  for stmt in vadp_stmts:
    if not stmt in replaced_stmts:
      new_vadp.append(stmt)



  return True,new_vadp

def cstrs_kirchoff(variables):
  cstrs = dict(map(lambda v: (v,unifylib.UnifyConstraint.NONE), \
                         variables))
  return cstrs

def apply_kirchoff(goal,rule,unif):
  law_var = tablib.LawVar(rule.law,rule.ident,tablib.LawVar.APPLY)
  stmt = []
  if isinstance(goal.variable, tablib.DSVar):
    var_name = goal.variable.var
    stmt.append(tablib.VADPSource(law_var,genoplib.Var(var_name)))
  else:
    stmt.append(tablib.VADPConn(law_var,goal.variable))
  return unif,stmt

def simplify_kirchoff(dev,vadp_stmts,rule):
  target_var = None
  sink_stmt = None
  # identify statements with rule variables
  for stmt in vadp_stmts:
    if isinstance(stmt, tablib.VADPConn) and \
       isinstance(stmt.source, tablib.LawVar) and \
       stmt.source.law == rule.law:
      sink_stmt = stmt
      sink_var = stmt.sink
      target_var = stmt.source
      break
    elif isinstance(stmt,tablib.VADPSource) and \
         isinstance(stmt.target, tablib.LawVar) and \
         stmt.port.law == rule.law:
      sink_stmt = stmt
      sink_var = VirtualSourceVar(stmt.dsexpr.name)
      target_var = stmt.port
      break
  # is there is no statement with rule variables
  if sink_stmt is None:
    return False,vadp_stmts

  # identify sources that are linked to the same sink
  sources = []
  replaced_stmts = [sink_stmt]
  for stmt in vadp_stmts:
    if isinstance(stmt,tablib.VADPConn) and \
       isinstance(stmt.sink, tablib.LawVar) and \
       stmt.sink.same_usage(target_var):
      sources.append(stmt.source)
      replaced_stmts.append(stmt)

  if len(sources) == 0:
    return vadp_stmts

  new_vadp = []
  for source in sources:
    new_vadp.append(tablib.VADPConn(source,sink_var))

  if isinstance(sink_stmt,tablib.VADPSink):
    new_vadp.append(VADPSink(sink_var, \
                             sink_stmt.ds_var))
  elif isinstance(sink_stmt,tablib.VADPSource):
    new_vadp.append(VADPSource(sink_var, \
                               sink_stmt.dsexpr))

  for stmt in vadp_stmts:
    if not stmt in replaced_stmts:
      new_vadp.append(stmt)

  return True,new_vadp

def cstrs_fuse_lut(variables):
  cstrs = dict(map(lambda v: (v,unifylib.UnifyConstraint.NONE), \
                         variables))
  cstrs['e'] = unifylib.UnifyConstraint.FUNCTION
  return cstrs


def apply_fuse_lut(goal,rule,unif):
  law_var = tablib.LawVar(rule.law,rule.ident,tablib.LawVar.APPLY)
  stmts = []
  if isinstance(goal.variable, tablib.DSVar):
    var_name = goal.variable.var
    stmts.append(tablib.VADPSource(law_var,genoplib.Var(var_name)))
  else:
    stmts.append(tablib.VADPConn(law_var,goal.variable))

  inpexpr = unif.get_by_name('a')
  coeff,base_expr = genoplib.factor_coefficient(inpexpr)
  assert(not base_expr is None)
  expr = unif.get_by_name('e')
  repl = {'T': genoplib.Mult(genoplib.Const(1.0/coeff),  \
                             genoplib.Var("y")) \
  }
  rule_var = vadplib.LawVar(rule.law,rule.ident)
  cfg = tablib.VADPConfig(rule_var,rule.mode)
  cfg.bind('e',expr.substitute(repl))
  stmts.append(cfg)

  

  new_unif = unifylib.Unification()
  new_unif.set_by_name('a', base_expr)

  return new_unif,stmts

def simplify_fuse_lut(dev,vadp,rule):
  target_stmt = None

  for stmt in vadp:
    print(">>>> %s" % stmt)

    if isinstance(stmt, tablib.VADPConfig) and \
       isinstance(stmt.target, tablib.LawVar) and \
       stmt.target.law == rule.law:
      target_stmt = stmt
      break

  print("FOUND: %s" % target_stmt)
  if target_stmt is None:
    return False,vadp

  new_vadp = []
  identifier = target_stmt.target.ident
  mode = target_stmt.mode
  lut = vadplib.PortVar(dev.get_block('lut'),identifier)
  lut_cfg = vadplib.VADPConfig(lut,"*")
  lut_cfg.bind('e', target_stmt.assigns['e'])
  new_vadp.append(lut_cfg)

  adc = vadplib.PortVar(dev.get_block('adc'),identifier)
  adc_mode = adc.block.modes[["m"] if mode[1] == "m" else ["h"]]
  adc_cfg = vadplib.VADPConfig(adc,adc_mode)
  new_vadp.append(adc_cfg)

  dac = vadplib.PortVar(dev.get_block('dac'),identifier)
  dac_mode = dac.block.modes[["dyn","m"] if mode[1] == "m" else ["dyn","h"]]
  dac_cfg = vadplib.VADPConfig(dac,dac_mode)
  new_vadp.append(dac_cfg)

  new_vadp.append(vadplib.VADPConn(adc.make_port_var('z'), \
                           lut.make_port_var('x')))

 
  new_vadp.append(vadplib.VADPConn(lut.make_port_var('z'), \
                           dac.make_port_var('x')))

  for stmt in vadp:
    if isinstance(stmt, tablib.VADPConn) and \
       isinstance(stmt.source, tablib.LawVar) and \
       rule.same_usage(stmt.source):
      new_vadp.append(vadplib.VADPConn(dac.make_port_var('z'), \
                               stmt.sink))
    elif isinstance(stmt, tablib.VADPConn) and \
       isinstance(stmt.sink, tablib.LawVar) and \
       rule.same_usage(stmt.sink):
      new_vadp.append(vadplib.VADPConn(stmt.source, \
                                       adc.make_port_var('x')))

    elif isinstance(stmt,tablib.VADPSource) and \
         isinstance(stmt.port, tablib.LawVar) and \
         rule.same_usage(stmt.port):
      new_vadp.append(vadplib.VAPSource(PortVar(dac,identifier,z), \
                                        stmt.source))
    else:
      print("unaffected: %s" % stmt)
      new_vadp.append(stmt)

    return True,new_vadp
