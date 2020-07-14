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
import compiler.lgraph_pass.route as routelib
import compiler.lgraph_pass.assemble as asmlib
import compiler.lgraph_pass.synth as synthlib
import compiler.lgraph_pass.rule as rulelib
import compiler.lgraph_pass.vadp as vadplib

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


def compile(board,prob,depth=12, \
            vadp_fragments=100, \
            assembly_num_copiers=10, \
            assembly_depth=3, \
            vadps=1, \
            adps=1):

    fragments = dict(map(lambda v: (v,[]), prob.variables()))
    compute_blocks = list(filter(lambda blk: \
                              blk.type == blocklib.BlockType.COMPUTE, \
                              board.blocks))

    # perform synthesis
    laws = get_laws()
    fragments = {}
    for variable in prob.variables():
        fragments[variable] = []
        expr = prob.binding(variable)
        print("> synthesizing %s = %s" % (variable,expr))
        for vadp in synthlib.search(compute_blocks,laws,variable,expr, \
                                    depth=depth):
            if len(fragments[variable]) >= vadp_fragments:
                break
            fragments[variable].append(vadp)

        print("var %s: %d fragments"  \
              % (variable,len(fragments[variable])))

    print("> assembling circuit")
    # insert copier blocks when necessary
    assemble_blocks = list(filter(lambda blk: \
                                  blk.type == blocklib.BlockType.ASSEMBLE, \
                                  board.blocks))

    circuit = {}
    block_counts = {}
    for variable in prob.variables():
        circuit[variable] = fragments[variable][0]

    vadp_circuits = []
    for circ in asmlib.assemble(assemble_blocks,circuit):
        vadp_circuits.append(circ)
        if len(vadp_circuits) >= vadps:
            break


    print("> routing circuit")
    for circ in vadp_circuits:
        vadp = routelib.route(board,circ)
        if not vadp is None:
            yield vadplib.to_adp(vadp)
