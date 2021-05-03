import hwlib.adp as adplib
import hwlib.block as blocklib
import ops.base_op as baseoplib
import ops.generic_op as genoplib
import ops.opparse as opparse
import numpy as np
import compiler.lscale_pass.lscale_ops as scalelib
import compiler.lscale_pass.lscale_harmonize as harmlib
import compiler.math_utils as mathutils

import ops.interval as ivallib


def _get_exprs(dev,dsinfo,cfg):
  blk = dev.get_block(cfg.inst.block)
  bl_mode = list(cfg.modes)[0]
  exprs = {}

  for port in blk.inputs.field_names() + blk.outputs.field_names():
    if dsinfo.has_expr(cfg.inst,port):
      exprs[port] = dsinfo.get_expr(cfg.inst,port)

  for datum in cfg.stmts_of_type(adplib.ConfigStmtType.CONSTANT):
    exprs[datum.name] = dsinfo.get_expr(cfg.inst,datum.name)

  return exprs


def __construct_expression_data_fields(cfg,apply_scale_transform=False):
  fn_bodies = {}
  for stmt in cfg.stmts_of_type(adplib.ConfigStmtType.EXPR):
        if apply_scale_transform:
            args = {}
            for v in stmt.expr.vars():
                inj = stmt.injs[v]
                args[v] = genoplib.Mult(genoplib.Const(inj), genoplib.Var(v))

            inj = stmt.injs[stmt.name]
            expr = genoplib.Mult(genoplib.Const(inj), \
                                 stmt.expr.substitute(args))
            fn_bodies[stmt.name] = expr
        else:
            fn_bodies[stmt.name] = stmt.expr

  return fn_bodies

def _generate_dsinfo_expr_recurse(dev,dsinfo,adp,apply_scale_transform=False):
  count = 0
  for conn in adp.conns:
    if not dsinfo.has_expr(conn.dest_inst,conn.dest_port):
      args = []
      for src_conn in \
          list(filter(lambda c: c.same_dest(conn), adp.conns)):
        if dsinfo.has_expr(src_conn.source_inst, \
                               src_conn.source_port):
          src_expr = dsinfo.get_expr(src_conn.source_inst, \
                                     src_conn.source_port)
          args.append(src_expr)
        else:
          args = None
          break

      if not args is None:
        expr = genoplib.sum(args)
        dsinfo.set_expr(conn.dest_inst,conn.dest_port,expr)
        count += 1

  for cfg in adp.configs:
    blk = dev.get_block(cfg.inst.block)
    bl_mode = list(cfg.modes)[0]
    inputs = _get_exprs(dev,dsinfo,cfg)
    fxns = __construct_expression_data_fields(cfg, \
                                              apply_scale_transform=apply_scale_transform)

    for out in blk.outputs:
      if dsinfo.has_expr(cfg.inst,out.name):
        continue

      orig_rel = out.relation[bl_mode].substitute(fxns).concretize()
      rel = orig_rel.substitute(inputs)
      all_inputs_bound = all(map(lambda v: v in inputs,orig_rel.vars()))

      if not all_inputs_bound:
          continue

      dsinfo.set_expr(cfg.inst,out.name,rel)
      count += 1

  return count



def generate_dynamical_system_expr_info(dsinfo,dev,program,adp,apply_scale_transform=False, \
                                        label_integrators_only=False):
  ds_ivals = dict(program.intervals())
  for config in adp.configs:
    for stmt in config.stmts_of_type(adplib.ConfigStmtType.PORT):
      if not stmt.source is None:
          expr = stmt.source
          if(apply_scale_transform):
              expr = genoplib.Mult(genoplib.Const(stmt.scf),expr)

          if not label_integrators_only or config.inst.block == "integ":
            dsinfo.set_expr(config.inst,stmt.name,expr)

    for datum in config.stmts_of_type(adplib.ConfigStmtType.CONSTANT):
        value = genoplib.Const(datum.value)
        if(apply_scale_transform):
              value = genoplib.Mult(genoplib.Const(datum.scf),value)

        dsinfo.set_expr(config.inst,datum.name,value)

  while _generate_dsinfo_expr_recurse(dev,dsinfo,adp, \
                                       apply_scale_transform=apply_scale_transform) > 0:
    pass

  #while _generate_dsinfo_expr_backprop(dev,dsinfo,adp,) > 0:
   # pass



def generate_dynamical_system_interval_info(dsinfo,dev,program,adp):
    ds_ivals = dict(program.intervals())
    for config in adp.configs:
        for stmt in config.stmts_of_type(adplib.ConfigStmtType.PORT):
            if not dsinfo.has_expr(config.inst,stmt.name):
                continue

            expr = dsinfo.get_expr(config.inst, stmt.name)
            ival = ivallib.propagate_intervals(expr,ds_ivals)
            dsinfo.set_interval(config.inst,stmt.name,ival)

        for datum in config.stmts_of_type(adplib.ConfigStmtType.CONSTANT):
            expr = dsinfo.get_expr(config.inst, datum.name)
            value = expr.compute()
            dsinfo.set_interval(config.inst,datum.name, \
                                ivallib.Interval.type_infer(value,value))


def generate_dynamical_system_info(dev,program,adp,apply_scale_transform=False, \
                                   label_integrators_only=False):
  dsinfo = scalelib.DynamicalSystemInfo()
  generate_dynamical_system_expr_info(dsinfo,dev,program,adp, \
                                      apply_scale_transform=apply_scale_transform, \
                                      label_integrators_only=label_integrators_only)
  generate_dynamical_system_interval_info(dsinfo,dev,program,adp)
  return dsinfo
