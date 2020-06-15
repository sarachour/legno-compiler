import itertools

import ops.opparse as parser
import random
import math
import logging
#import compiler.lgraph_pass.route as lgraph_route
#from compiler.lgraph_pass.rules import get_rules
#import compiler.lgraph_pass.to_abs_op as lgraphlib_aop
#import compiler.lgraph_pass.to_abs_circ as lgraphlib_acirc
#import compiler.lgraph_pass.make_fanouts as lgraphlib_mkfan
#import compiler.lgraph_pass.util as lgraphlib_util
#import hwlib.abs as acirc
#import hwlib.props as prop
#from hwlib.config import Labels
#import ops.aop as aop

import hwlib.block as blocklib
import compiler.lgraph_pass.assemble as asmlib
import compiler.lgraph_pass.tableau as tablib
import compiler.lgraph_pass.rule as rulelib

#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('lgraph')
#logger.setLevel(logging.ERROR)
logger.setLevel(logging.INFO)

def bind_namespace(node,namespace,ids=[]):
    if node.id in ids:
        return

    node.set_namespace(namespace)
    if isinstance(node,acirc.AInput) and \
       not node.source is None:
        new_namespace = node.label
        rslv_node,_ = node.source
        bind_namespace(rslv_node,new_namespace,ids=ids + [node.id])

    else:
        for subn in node.subnodes():
            bind_namespace(subn,namespace,ids=ids + [node.id])

def compile_compute_fragments(board,prob,n_xforms):
    frag_node_map= {}
    frag_output_map= {}
    xform_map = {}
    rules = get_rules(board)
    for var,expr in prob.bindings():
        print("-> Fragment %s = %s" % (var,expr))
        abs_expr = lgraphlib_aop.make_abstract(expr)
        frag_node_map[var] = []
        frag_output_map[var] = []
        xform_map[var] = []
        print(abs_expr)
        for n_xforms,xform_abs_expr in abs_expr.xform(rules,n_xforms):
            xform_map[var].append(xform_abs_expr)
            for node,output in lgraphlib_acirc.to_abs_circ(board,xform_abs_expr):
                if isinstance(node,acirc.ABlockInst):
                    node.config.set_label(output,var,kind=Labels.OUTPUT)

                if acirc.AbsCirc.feasible(board,[node]):
                    frag_node_map[var].append(node)
                    frag_output_map[var].append(output)


    return xform_map,frag_node_map,frag_output_map


def compile_sample_fragments_and_add_fanouts(board,frag_node_map, \
                                             frag_output_map):
    while True:
        frag_nodes = {}
        frag_outputs = {}
        logger.info("-> sampling circuit")
        choices = lgraphlib_util.sample(frag_node_map)
        for variable,index in choices.items():
            frag_nodes[variable],_ = \
                                     frag_node_map[variable][index].copy()
            frag_outputs[variable] = frag_output_map[variable][index]

        # compute any references/stubs
        refs,stubs = lgraphlib_mkfan.count_var_refs(frag_nodes)

        subcs = {}
        skip_circuit = False
        # number of free fanouts for variable references
        free_fanouts = board.num_blocks("fanout") - \
                       acirc.AbsCirc.count_instances(board,\
                                    frag_nodes.values())["fanout"]

        for var_name,frag_node in frag_nodes.items():
            frag_output = frag_outputs[var_name]
            subcs[var_name] = []
            # make n copies of each variable for routing purposes.
            for sources,cnode in \
                lgraphlib_mkfan.copy_signal(board,frag_node,frag_output,
                                          refs[var_name], var_name, free_fanouts):

                other_frags = [v for k,v in frag_nodes.items() \
                               if k != var_name]

                if acirc.AbsCirc.feasible(board,[cnode]+other_frags):
                    subcs[var_name].append((sources,cnode))

            if len(subcs[var_name]) == 0:
                skip_circuit = True
                break

        if skip_circuit:
            continue

        logger.info("--- Fan outs ---")
        for var,frags in subcs.items():
            logger.info("%s: %d" % (var,len(frags)))


        yield subcs

def remap_vadp_identifiers(subcircuit_optmap):
        variables = []
        subcirc_options = []
        subcirc_sources = {}
        subcirc_nodes = {}
        for variable,subcirc_opt in subcircuit_optmap.items():
            variables.append(variable)
            subcirc_options.append(range(0,len(subcirc_opt)))
            subcirc_sources[variable] = []
            subcirc_nodes[variable] = []
            for source,node in subcirc_opt:
                subcirc_sources[variable].append(source)
                subcirc_nodes[variable].append(node)


        for select_idx,selection in \
            enumerate(itertools.product(*subcirc_options)):
            source_map = {}
            node_map = {}
            for variable,index in zip(variables,selection):
                logger.info(variable)
                source_map[variable] = subcirc_sources[variable][index]
                node_map[variable] = subcirc_nodes[variable][index]

            yield select_idx,source_map,node_map

def compile(board,prob,depth=3, \
            max_abs_circs=100, \
            max_fanout_circs=1, \
            max_conc_circs=1):

    print("---- Assembling Fragments -----")
    xform_map,frag_node_map,frag_output_map = \
            compile_compute_fragments(board,prob,n_xforms=depth)

    logger.info("--- Fragments ---")
    for var,frags in frag_node_map.items():
        logger.info("====== %s ====" % (var))
        logger.info("# xforms: %d" %  len(xform_map[var]))
        logger.info("# unique-xforms: %d" %  len(set(map(lambda x: str(x),xform_map[var]))))
        for xform in xform_map[var]:
            logger.info(xform)
        logger.info("# frags: %d" %  len(frags))
        if len(frags) == 0:
            raise Exception("cannot model variable <%s>" % var)

    try_abs = lgraphlib_util.TryObject('abs_circ',max_abs_circs,None)
    try_merge = lgraphlib_util.TryObject('merge_circ',max_fanout_circs,100)
    try_conc = lgraphlib_util.TryObject('conc_circ',max_conc_circs,None)

    for abs_idx, subcircuits_optmap in \
        try_abs.enumerate(compile_sample_fragments_and_add_fanouts(board, \
                                                                 frag_node_map,
                                                                   frag_output_map), \
                          do_succeed=False):


        try_merge.clear()
        try_conc.clear()
        conc_idx = 0
        logger.info(">>> combine fragments <<<")
        for merge_idx,source_map,node_map in \
            try_merge.iterate(compile_combine_fragments(subcircuits_optmap),do_succeed=False):

            refs,stubs = lgraphlib_mkfan.count_var_refs(node_map)
            n_conc = 0;
            logger.info(">>> compute matches from stubs to sources <<<")
            for stub_src_idx,mapping in \
                enumerate(lgraphlib_mkfan.match_stubs_to_sources(source_map,stubs)):

                if not try_conc.successes_left():
                    logger.info("-> found %d/%d conc circuits" % \
                                (n_conc,max_conc_circs))
                    break
                logger.info(">>> connect stubs to sources <<<")
                succ = lgraphlib_mkfan.connect_stubs_to_sources(board,
                                                              node_map, \
                                                              mapping)
                if not succ:
                    logger.info("=> FAILED TO CONNECT")
                    #input("[press any key to continue]")
                    continue

                logger.info(">>> bind namespaces <<<")
                for var,node in node_map.items():
                    bind_namespace(node,var)

                logger.info(">>> route <<<")
                for route_index,conc_circ in try_conc.enumerate(lgraph_route.route(board,
                                                                                 prob,
                                                                                 node_map,
                                                                                 max_failures=1000,
                                                                                 max_resolutions=100)):

                    indices = [abs_idx,conc_idx]
                    try_merge.succeed()
                    try_abs.succeed()
                    index_str = "x".join(map(lambda i: str(i), indices))
                    yield index_str,conc_circ
                    conc_idx += 1
                    break


def get_laws():
    return [
        {
            'name':'kirchoff',
            'expr': parser.parse_expr('a+b'),
            'type': blocklib.BlockSignalType.ANALOG,
            'vars': {
                'a':blocklib.BlockSignalType.ANALOG, \
                'b':blocklib.BlockSignalType.ANALOG
            },
            'cstrs': rulelib.cstrs_kirchoff,
            'apply': rulelib.apply_kirchoff,
            'simplify': rulelib.simplify_kirchoff
        },
        {
            'name':'flip_sign',
            'expr':parser.parse_expr('-a'),
            'type': blocklib.BlockSignalType.ANALOG,
            'vars': {
                'a':blocklib.BlockSignalType.ANALOG
            },
            'cstrs': rulelib.cstrs_flip,
            'apply': rulelib.apply_flip,
            'simplify': rulelib.simplify_flip
        }
    ]


def remap_vadp_identifiers(insts,fragment):
  mappings = {}
  def get_identifier(block,inst):
    if not (block.name,inst) in mappings:
      if not block.name in insts:
        insts[block.name] = 0

      mappings[(block.name,inst)] = insts[block.name]
      insts[block.name] += 1

    return mappings[(block.name,inst)]

  for stmt in fragment:
    if isinstance(stmt,tablib.VADPSource) or \
       isinstance(stmt,tablib.VADPSink):
      new_stmt = stmt.copy()
      new_stmt.port.ident = get_identifier(stmt.port.block, \
                                      stmt.port.ident)
      yield new_stmt

    elif isinstance(stmt,tablib.VADPConn):
        new_stmt = stmt.copy()
        new_stmt.source.ident = get_identifier(stmt.source.block, \
                                               stmt.source.ident)
        new_stmt.sink.ident = get_identifier(stmt.sink.block, \
                                             stmt.sink.ident)

        yield new_stmt

    elif isinstance(stmt,tablib.VADPConfig):
        new_stmt = stmt.copy()
        new_stmt.ident = get_identifier(stmt.block, \
                                   stmt.ident)
        yield new_stmt

    else:
        raise Exception("not handled: %s" % stmt)

def compile(board,prob,depth=3, \
            vadp_fragments=100, \
            vadps=1, \
            adps=1):

    fragments = dict(map(lambda v: (v,[]), prob.variables()))
    compute_blocks = list(filter(lambda blk: \
                              blk.type == blocklib.BlockType.COMPUTE, \
                              board.blocks))

    laws = get_laws()
    fragments = {}
    for variable in prob.variables():
        fragments[variable] = []
        expr = prob.binding(variable)
        for vadp in tablib.search(compute_blocks,laws,variable,expr):
            if len(fragments[variable]) >= vadp_fragments:
                break

            fragments[variable].append(vadp)

    copy_blocks = list(filter(lambda blk: \
                              blk.type == blocklib.BlockType.COPY, \
                              board.blocks))

    circuit = {}
    block_counts = {}
    for variable in prob.variables():
        circuit[variable] = list(remap_vadp_identifiers(block_counts, \
                                                        fragments[variable][0]))

    for circ in asmlib.assemble(copy_blocks,circuit):
        print(circ)
    raise NotImplementedError
