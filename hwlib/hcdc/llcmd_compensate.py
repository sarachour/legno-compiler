import runtime.models.exp_delta_model as deltalib

import hwlib.block as blocklib
import hwlib.adp as adplib

import hwlib.hcdc.llenums as llenums

import ops.generic_op as genoplib
import ops.op as oplib
import util.util as util

def get_experimental_model(board,blk,loc,cfg,calib_obj):
    calib_codes = list(filter(lambda st: isinstance(st.impl, blocklib.BCCalibImpl), \
                              blk.state))

    if len(calib_codes) == 0:
        return

    calib_cfgs = deltalib.get_calibrated(board,blk,loc,cfg,calib_obj)
    if len(calib_cfgs) == 0:
        print(cfg)
        raise Exception("not calibrated model_number=%s calib=%s" % (board.model_number, \
                                                                    calib_obj))

    calib_cfg = calib_cfgs[0]

    for st in calib_codes:
        cfg[st.name].value = calib_cfg.config[st.name].value

    return calib_cfg


def get_compensation_parameters(model,init_cond=False):
    spec = model.spec

    if not init_cond:
        variables = spec.relation.vars()
    else:
        variables = spec.relation.init_cond.vars()

    comp_pars = list(filter(lambda par: par.name in variables, \
                         spec.get_params_of_type(blocklib.DeltaParamType.CORRECTABLE)))
    asm_pars = list(filter(lambda par: par.name in variables, \
                           spec.get_params_of_type(blocklib.DeltaParamType.LL_CORRECTABLE)))

    if len(comp_pars) == 0 or len(asm_pars) == 0:
        print(model.config)
        raise Exception("cannot compensate: no parameters (vars=%s)" % variables)

    if len(comp_pars) > 1 or len(asm_pars) > 1:
        print(model.config)
        raise Exception("cannot compensate: too many parameters (corr=%s, llcorr=%s)" \
                        % (comp_pars,asm_pars))

    gain_par = model.params[comp_pars[0].name]
    offset_par = model.params[asm_pars[0].name]
    return gain_par,offset_par


def compute_expression_fields(board,adp,cfg,compensate=True):
    print(cfg)
    blk = board.get_block(cfg.inst.block)

    if(len(blk.data) < 1):
        return

    data = list(filter(lambda d: d.type == blocklib.BlockDataType.EXPR, \
                        blk.data))

    if(len(data) < 1):
        return

    assert(len(data) == 1)
    # only allowed to have one output.
    output_port = blk.outputs.singleton()
    calib_obj = llenums.CalibrateObjective(adp.metadata[adplib.ADPMetadata.Keys.RUNTIME_CALIB_OBJ])

    rel = output_port.relation[cfg.mode]
    fn_call= util.singleton(filter(lambda n: n.op == oplib.OpType.CALL, rel.nodes()))
    fn_spec=fn_call.func
    fn_params = fn_call.values
    data_expr_field_name = util.singleton(fn_spec.expr.vars())
    data_expr_field = cfg.get(data_expr_field_name)

    # build offset map
    repls = {}
    for input_port, func_arg in zip(fn_call.values,fn_spec.func_args):
        if compensate:
            assert(input_port.op == oplib.OpType.VAR)
            conn = util.singleton(adp.incoming_conns(blk.name, cfg.inst.loc, input_port.name))
            src_block = board.get_block(conn.source_inst.block)
            src_cfg = adp.configs.get(conn.source_inst.block, conn.source_inst.loc)
            model = get_experimental_model(board, \
                                           src_block, \
                                           conn.source_inst.loc, \
                                           src_cfg,calib_obj)
            gain,offset = get_compensation_parameters(model,init_cond=False)
        else:
            gain,offset = 1.0,0.0

        inj = data_expr_field.injs[func_arg]
        repls[func_arg] = genoplib.Mult(genoplib.Const(inj), \
                                        genoplib.Add( \
                                                      genoplib.Var(func_arg), \
                                                      genoplib.Const(-offset)
                                                     ))

        print("inp-var %s inj=%f offset=%f" % (func_arg,inj,offset))

    # compute model of output block
    if compensate:
        conn = util.singleton(adp.outgoing_conns(blk.name, cfg.inst.loc, output_port.name))
        dest_block = board.get_block(conn.dest_inst.block)
        dest_cfg = adp.configs.get(conn.dest_inst.block, conn.dest_inst.loc)

        model = get_experimental_model(board, \
                                       dest_block, \
                                       dest_cfg.inst.loc, \
                                       dest_cfg,calib_obj)
        gain,offset = get_compensation_parameters(model,False)

    else:
        gain,offset = 1.0,0.0

    inj = data_expr_field.injs[data_expr_field.name]
    print("out-var %s inj=%f gain=%f offset=%f" % (data_expr_field.name, \
                                                   inj,gain,offset))

    func_impl = genoplib.Mult(genoplib.Const(inj), \
                              data_expr_field.expr.substitute(repls))
    print("func-expr: %s" % func_impl)
    rel_impl = genoplib.Add( \
                        rel.substitute({data_expr_field.name:func_impl}), \
                        genoplib.Const(-offset/gain) \
                       )
    print("rel-expr: %s" % rel_impl)

    print("--- building lookup table ---")
    output_port = blk.outputs.singleton()
    input_port = blk.inputs.singleton()
    final_expr = rel_impl.concretize()
    print(final_expr)
    input_values = input_port.quantize[cfg.mode] \
                             .get_values(input_port \
                                         .interval[cfg.mode])
    lut_outs = []
    for val in input_values:
        out = final_expr.compute({input_port.name:val})
        lut_outs.append(out)


    cfg[data_expr_field.name].outputs= lut_outs
    cfg[data_expr_field.name].inputs = input_values
    cfg[data_expr_field.name].input_port = input_port.name
    return lut_outs



def compute_constant_fields(board,adp,cfg,compensate=True):
    blk = board.get_block(cfg.inst.block)
    data = list(filter(lambda d: d.type == blocklib.BlockDataType.CONST, \
                        blk.data))
    if(len(data) < 1):
        return

    assert(len(data) == 1)
    data_field = data[0]

    old_val = cfg[data_field.name].value
    if compensate:
        calib_obj = llenums.CalibrateObjective(adp.metadata[adplib.ADPMetadata.Keys.RUNTIME_CALIB_OBJ])
        model = get_experimental_model(board, \
                                       blk, \
                                       cfg.inst.loc, \
                                       cfg,calib_obj)

        is_init_cond = model.is_integration_op
        gain,offset = get_compensation_parameters(model,is_init_cond)
    else:
        gain,offset = 1.0,0.0

    cfg[data_field.name].value *= cfg[data_field.name].scf
    cfg[data_field.name].value -= offset

    print("=== field %s ===" % data_field)
    print("scf=%f" % cfg[data_field.name].scf)
    print("gain=%f" % gain)
    print("offset=%f" % offset)
    print("value=%f" % old_val);
    print("=> updated data field %s: %f -> %f" % (data_field, \
                                                  old_val, \
                                                  cfg[data_field.name].value))

