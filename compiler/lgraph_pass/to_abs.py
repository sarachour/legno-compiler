
def tac_integ(board,ast):
    for deriv,deriv_output in to_abs_circ(board,ast.input(0)):
        ic = ast.input(1)
        if not (ic.op == aop.AOpType.CPROD and \
                ic.input.op == aop.AOpType.CONST):
            raise Exception("unexpected ic: <%s>" % ic)

        init_cond = ic.value
        node = acirc.ANode.make_node(board,"integrator")
        node.config.set_comp_mode("*")
        node.config.set_dac("ic",init_cond)
        acirc.ANode.connect(deriv,deriv_output,node,"in")
        yield node,"out"


def tac_vprod(board,ast):
    if len(ast.inputs) == 1:
        for node,output in to_abs_circ(board,ast.input(0)):
            yield node,output

    else:
        multiplier = board.block("multiplier")
        for levels in \
            enumerate_tree(multiplier,len(ast.inputs),
                           permute_input=True,
                           prop=prop.CURRENT):

            new_inputs = list(map(lambda inp: \
                                  list(to_abs_circ(board,inp)), \
                                  ast.inputs))
            # for each combination of inputs
            for combo in itertools.product(*new_inputs):
                free_ports,out_block,out_port = \
                                                build_tree_from_levels(
                                                    board,
                                                    levels,
                                                    multiplier,
                                                    input_tree=True,
                                                    mode='mul',
                                                    prop=prop.CURRENT
                                                )

                for assigns in input_level_combos(free_ports,combo):
                    out_block_c,copier = out_block.copy()
                    for (_dstblk,dstport),(_srcblk,srcport) in assigns:
                        dstblk = copier.get(_dstblk)
                        srcblk,_ = _srcblk.copy()
                        acirc.ANode.connect(srcblk,srcport, \
                                            dstblk,dstport)
                    validate_fragment(out_block_c)
                    yield out_block_c,out_port

def tac_cprod(board,ast):
    if ast.input.op == aop.AOpType.CONST:
        for result in to_abs_circ(board,ast.input):
            yield result
    else:
        #for qnode,qnode_output in to_abs_circ(board,ast.input):
        # hail mary, assume we can scale our way around this
        #    yield qnode,qnode_output

        for qnode,qnode_output in to_abs_circ(board,ast.input):
            node = acirc.ANode.make_node(board,"multiplier")
            node.config.set_comp_mode("vga")\
                       .set_dac("coeff",ast.value)
            acirc.ANode.connect(qnode,qnode_output,node,"in0")
            yield node,"out"




def to_abs_circ(board,ast):
    print(ast)
    input("TODO: handle constant propagation")
    if ast.op == aop.AOpType.INTEG:
        for result in tac_integ(board,ast):
            yield result

    elif ast.op == aop.AOpType.VPROD:
        for result in tac_vprod(board,ast):
            yield result

    elif ast.op == aop.AOpType.CPROD:
        for result in tac_cprod(board,ast):
            yield result

    elif ast.op == aop.AOpType.CONST:
        node = acirc.ANode.make_node(board,"tile_dac")
        node.config.set_comp_mode('*')
        node.config.set_dac("in",ast.value)
        yield node,"out"

    elif ast.op == aop.AOpType.VAR:
        stub = acirc.AInput(ast.name)
        yield stub,"out"

    elif ast.op == aop.AOpType.EXTVAR:
        node = acirc.ANode.make_node(board,"ext_chip_in")
        node.config.set_label("in", ast.name,kind=Labels.DYNAMIC_INPUT)
        node.config.set_comp_mode("*")
        yield node,"out"

    elif ast.op == aop.AOpType.SUM:
        new_inputs = list(map(lambda inp: list(to_abs_circ(board,inp)), \
                                 ast.inputs))

        for combo in itertools.product(*new_inputs):
            join = acirc.AJoin()
            for node,out in combo:
                nnode,_ = node.copy()
                assert(not nnode is None)
                acirc.ANode.connect(nnode,out,join,"in")

            yield join,"out"

    elif ast.op == aop.AOpType.EMIT:
        for in_node,in_port in to_abs_circ(board,ast.input(0)):
            node = acirc.ANode.make_node(board,"ext_chip_out")
            node.config.set_comp_mode("*")
            acirc.ANode.connect(in_node,in_port,node,"in")
            yield node,"out"

    else:
        raise Exception("unsupported: %s" % ast)
