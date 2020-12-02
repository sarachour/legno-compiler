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
from compiler.lgraph_pass.rules.kirch import KirchhoffRule
from compiler.lgraph_pass.rules.lutfuse import FuseLUTRule


def get_laws(dev):
    return [KirchhoffRule(), FuseLUTRule(dev)]
    return [
        {
            'name':'kirchoff',
            'expr': {"*": parser.parse_expr('a+b')},
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
            'name':'lut-fuse',
            'expr': { \
                      ('m','m'): parser.parse_expr('2.0*f((0.5*a))', 
                                                   {'f':(['y'],parser.parse_expr('e'))}), \
                      ('h','m'): parser.parse_expr('2.0*f((0.05*a))', 
                                                   {'f':(['y'],parser.parse_expr('e'))}), \
                      ('h','h'): parser.parse_expr('20.0*f((0.05*a))',
                                                   {'f':(['y'],parser.parse_expr('e'))}), \
                      ('m','h'): parser.parse_expr('20.0*f((0.5*a))',
                                                   {'f':(['y'],parser.parse_expr('e'))}), \
            },
            'type': blocklib.BlockSignalType.ANALOG,
            'vars': {
                'a':blocklib.BlockSignalType.ANALOG
            },
            'cstrs': rulelib.cstrs_fuse_lut,
            'apply': rulelib.apply_fuse_lut,
            'simplify': rulelib.simplify_fuse_lut
        },
        {
            'name':'flip_sign',
            'expr':{"*":parser.parse_expr('-a')},
            'type': blocklib.BlockSignalType.ANALOG,
            'vars': {
                'a':blocklib.BlockSignalType.ANALOG
            },
            'cstrs': rulelib.cstrs_flip,
            'apply': rulelib.apply_flip,
            'simplify': rulelib.simplify_flip
        }
    ]


def compile(board,prob,
            vadp_fragments=100, \
            synth_depth=12, \
            asm_frags=10, \
            vadps=1, \
            adps=1, \
            routes=1):

    fragments = dict(map(lambda v: (v,[]), prob.variables()))
    compute_blocks = list(filter(lambda blk: \
                              blk.type == blocklib.BlockType.COMPUTE, \
                              board.blocks))

    # perform synthesis
    laws = get_laws(board)
    fragments = {}
    for variable in prob.variables():
        fragments[variable] = []
        expr = prob.binding(variable)
        print("> SYNTH %s = %s" % (variable,expr))
        for vadp in synthlib.search(board, \
                                    compute_blocks,laws,variable,expr, \
                                    depth=synth_depth):
            if len(fragments[variable]) >= vadp_fragments:
                break
            fragments[variable].append(vadp)

        print("VAR %s: %d fragments"  \
              % (variable,len(fragments[variable])))
        if len(fragments[variable]) == 0:
            raise Exception("could not synthesize any fragments for <%s>" % variable)

    print("> assembling circuit")
    # insert copier blocks when necessary
    assemble_blocks = list(filter(lambda blk: \
                                  blk.type == blocklib.BlockType.ASSEMBLE, \
                                  board.blocks))

    circuit = {}
    block_counts = {}
    vadp_circuits = []
    while len(vadp_circuits) < vadps:
        for variable in prob.variables():
            circuit[variable] = random.choice(fragments[variable])

        for circ in asmlib.assemble(assemble_blocks,circuit, \
                                    n_asm_frags=asm_frags):
            vadp_circuits.append(circ)
            if len(vadp_circuits) >= vadps:
                break


    print("> routing circuit")
    adp_circuits = []
    for circ in vadp_circuits:
        for vadp in routelib.route(board,circ):
            adp = vadplib.to_adp(vadp)
            adp_circuits.append(adp)
            yield adp
            if len(adp_circuits) > adps:
                break
