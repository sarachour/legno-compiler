import ops.scop as scop
import ops.op as ops
import ops.interval as interval
from enum import Enum
import compiler.lscale_pass.lscale_common as lscale_common
import compiler.lscale_pass.lscale_util as lscale_util
import logging

class ExprVisitor:

  def __init__(self,scenv,circ,block,loc,port):
    self.scenv = scenv
    self.circ = circ
    self.block = block
    self.loc = loc
    self.port = port

  def visit(self):
    raise NotImplementedError

  def get_coeff(self,handle=None):
    raise NotImplementedError

  def visit_expr(self,expr):
    result = None
    if expr.op == ops.OpType.CONST:
      result = self.visit_const(expr)

    elif expr.op == ops.OpType.VAR:
      result = self.visit_var(expr)

    elif expr.op == ops.OpType.MULT:
      result = self.visit_mult(expr)

    elif expr.op == ops.OpType.SGN:
      result = self.visit_sgn(expr)

    elif expr.op == ops.OpType.ABS:
      result = self.visit_abs(expr)

    elif expr.op == ops.OpType.COS:
      result = self.visit_cos(expr)

    elif expr.op == ops.OpType.SIN:
      result = self.visit_sin(expr)

    elif expr.op == ops.OpType.ADD:
      result = self.visit_add(expr)

    elif expr.op == ops.OpType.MIN:
      result = self.visit_min(expr)

    elif expr.op == ops.OpType.MAX:
      result = self.visit_max(expr)

    elif expr.op == ops.OpType.POW:
      result = self.visit_pow(expr)

    elif expr.op == ops.OpType.INTEG:
      result = self.visit_integ(expr)

    else:
        raise Exception("unhandled <%s>" % expr)

    assert(not result is None)
    return result


  def visit_const(self,c):
    raise NotImplementedError

  def visit_var(self,v):
    raise NotImplementedError

  def visit_pow(self,e):
    raise NotImplementedError

  def visit_add(self,e):
    raise NotImplementedError

  def visit_min(self,m):
    raise NotImplementedError

  def visit_max(self,m):
    raise NotImplementedError

  def visit_mult(self,m):
    raise NotImplementedError

  def visit_sgn(self,s):
    raise NotImplementedError

class SCFPropExprVisitor(ExprVisitor):

  def __init__(self,scenv,circ,block,loc,port):
    ExprVisitor.__init__(self,scenv,circ,block,loc,port)


  def coeff(self,handle):
    block,loc,port = self.block,self.loc,self.port
    pars = lscale_common.get_parameters(self.scenv,self.circ, \
                                       block,loc,port,handle)

    return pars['hw_gain']

  def visit_const(self,expr):
    return scop.SCConst(1.0)

  def visit_pow(self,expr):
    expr1 = self.visit_expr(expr.arg(0))
    expr2 = self.visit_expr(expr.arg(1))
    if expr.arg(1).op == ops.OpType.CONST:
      self.scenv.eq(expr2, scop.SCConst(1.0), 'expr-visit-pow')
      return scop.expo(expr1, expr.arg(1).value)
    else:
      self.scenv.eq(expr1, scop.SCConst(1.0), 'expr-visit-pow')
      self.scenv.eq(expr2, scop.SCConst(1.0), 'expr-visit-pow')
      return scop.SCConst(1.0)

  def visit_var(self,expr):
    block,loc = self.block,self.loc
    scvar = self.scenv.get_scvar(block.name,loc,expr.name)
    if self.scenv.has_inject_var(block.name,loc,expr.name):
      injvar = self.scenv.get_inject_var(block.name,loc,expr.name)
      expr = scop.SCMult(scop.SCVar(scvar),scop.SCVar(injvar))
      self.scenv.eq(expr, scop.SCConst(1.0), 'expr-visit-inj')
      return expr
    else:
      return scop.SCVar(scvar)


  def visit_mult(self,expr):
    expr1 = self.visit_expr(expr.arg1)
    expr2 = self.visit_expr(expr.arg2)
    return scop.SCMult(expr1,expr2)

  def visit_add(self,expr):
    expr1 = self.visit_expr(expr.arg1)
    expr2 = self.visit_expr(expr.arg2)
    self.scenv.eq(expr1,expr2,'expr-visit-add')
    return expr1

  def visit_randfun(self,expr):
    expr1 = self.visit_expr(expr.arg(0))
    return scop.SCConst(1.0)

  def visit_sgn(self,expr):
    expr1 = self.visit_expr(expr.arg(0))
    return scop.SCConst(1.0)

  def visit_abs(self,expr):
    expr = self.visit_expr(expr.arg(0))
    return expr

  def visit_sqrt(self,expr):
    expr = self.visit_expr(expr.arg(0))
    new_expr = scop.expo(expr,0.5)
    return new_expr

  def visit_max(self,expr):
    expr1 = self.visit_expr(expr.arg(0))
    expr2 = self.visit_expr(expr.arg(1))
    self.scenv.eq(expr1,expr2,'expr-visit-max')
    return expr1

  def visit_min(self,expr):
    expr1 = self.visit_expr(expr.arg(0))
    expr2 = self.visit_expr(expr.arg(1))
    self.scenv.eq(expr1,expr2,'expr-visit-min')
    return expr1


  def visit_cos(self,expr):
    expr = self.visit_expr(expr.arg(0))
    self.scenv.eq(expr, scop.SCConst(1.0), 'expr-visit-cos')
    return scop.SCConst(1.0)

  def visit_sin(self,expr):
    return self.visit_cos(expr)

  def visit_integ(self,expr):
    scenv = self.scenv
    block,loc,port = self.block,self.loc,self.port
    # config
    scexpr_ic = self.visit_expr(expr.init_cond)
    scexpr_deriv = self.visit_expr(expr.deriv)

    scvar_deriv = scop.SCVar(scenv.get_scvar(block.name,loc,port, \
                                          handle=expr.deriv_handle))
    scvar_state = scop.SCVar(scenv.get_scvar(block.name,loc,port, \
                                          handle=expr.handle))
    scvar_ic = scop.SCVar(scenv.get_scvar(block.name,loc,port, \
                                          handle=expr.ic_handle))
    coeff_deriv = self.coeff(expr.deriv_handle)
    coeff_state = self.coeff(expr.handle)
    coeff_ic = self.coeff(expr.ic_handle)

    #lscale_util.log_debug("deriv: coeff=%s var=%s" % (coeff_deriv,scvar_deriv))
    #lscale_util.log_debug("stvar: coeff=%s var=%s" % (coeff_state,scvar_state))
    #lscale_util.log_debug("ic:    coeff=%s var=%s" % (coeff_ic,scvar_ic))
    #lscale_util.log_debug("deriv-expr: %s" % scexpr_deriv)
    #lscale_util.log_debug("ic-expr: %s" % scexpr_ic)
    scenv.eq(scop.SCMult(scexpr_ic,coeff_ic), scvar_ic,'expr-visit-integ')
    scenv.eq(scvar_ic, scvar_state,'expr-visit-integ')

    scenv.eq(scop.SCMult(scexpr_deriv, coeff_deriv), scvar_deriv, \
            'expr-visit-integ')

    scexpr_state = scop.SCMult(scop.SCVar(scenv.tau(), \
                                      exponent=-1), scvar_deriv)

    scenv.eq(scop.SCMult(scexpr_state, coeff_state),  \
            scvar_state,'expr-visit-integ')

    scenv.use_tau()
    return scvar_state

  def visit(self):
      block,loc = self.block,self.loc
      config = self.circ.config(block.name,loc)
      if not config.has_expr(self.port):
        expr = block.get_dynamics(config.comp_mode,self.port)
      else:
        expr = config.expr(self.port,inject=False)

      lhsexpr = scop.SCVar(self.scenv.get_scvar(block.name,loc,self.port))
      rhsexpr = self.visit_expr(expr)
      if self.scenv.has_inject_var(block.name,loc,self.port):
        injvar = self.scenv.get_inject_var(block.name,loc,self.port)
        self.scenv.eq(rhsexpr, scop.SCConst(1.0), 'expr-visit-inj')
        rhsexpr = scop.SCMult(rhsexpr,scop.SCVar(injvar))

      coeffvar = self.coeff(None)
      total_rhsexpr = scop.SCMult(rhsexpr,coeffvar)
      self.scenv.eq(lhsexpr,total_rhsexpr, 'expr-visit-out')
