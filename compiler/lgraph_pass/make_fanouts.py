import hwlib.abs as acirc
import hwlib.props as prop
import compiler.lgraph_pass.util as lgraph_util
from hwlib.config import Labels
import itertools

def copy_signal(board,node,output,n_copies,label,max_fanouts):
    sources = []
    if n_copies <= 1:
        #assert(not isinstance(node,acirc.AJoin))
        sources ={0:[(node,output)]}
        yield sources,node

    fanout = board.block("fanout")
    fanout_modes={}
    for mode in fanout.comp_modes:
        fanout_modes[mode] = {}
        for out in fanout.outputs:
            fanout_modes[mode][out] = fanout.get_dynamics(mode,out).coefficient()

    for levels in lgraph_util.enumerate_tree(fanout,n_copies,
                                 max_blocks=max_fanouts,
                                 permute_input=False):
        free_ports,c_node,c_input,fanout_nodes = lgraph_util\
                                     .build_tree_from_levels(board,
                                                             levels,
                                                             fanout,
                                                             ['out1','out0','out2'],
                                                             'in',
                                                             input_tree=False,
                                                             mode=None,
                                                             prop=prop.CURRENT
                                     )

        n_free_ports = dict(map(lambda node_id: (node_id,0),fanout_nodes.keys()))
        for level,ports in free_ports.items():
            for port_node,port in ports:
                port_node.config.set_label(port,label,kind=Labels.OUTPUT)
                n_free_ports[port_node.id] += 1

        for bound_node_id,bound_node in fanout_nodes.items():
            if n_free_ports[bound_node_id] == 0:
                signs = dict(map(lambda out: (out,1), fanout.outputs))
                valid_modes = list(get_valid_modes(fanout_modes,signs))
                bound_node.config.set_comp_mode(valid_modes[0])
        # if there are no free ports on this copier,
        # then this block must only produce positive signals
        # since it's providing signals for the other copiers.

        new_node,ctx = node.copy()
        acirc.ANode.connect(new_node,output,c_node,c_input)

        print("<< number copies %d >>" % n_copies)
        total_copies = 0
        for level,ports in free_ports.items():
            total_copies += len(ports)
        if(total_copies < n_copies):
            print("WARNING: failed to build hierarchy %d<%d" \
                  % (total_copies,n_copies))
            continue

        yield free_ports,c_node



def get_valid_modes(mode_map,scf_map):
  for mode,mode_scfs in mode_map.items():
    is_match = True
    for port,scf in scf_map.items():
      if scf != mode_scfs[port]:
        is_match = False

    if is_match:
      yield mode

def cs2s_join(board,node,outputs,stubs):
    assert(len(outputs) == 1)
    assert(len(stubs) == 1)
    output,stub = outputs[0],stubs[0]
    assert(stub.coefficient == 1.0)

def cs2s_blockinst(board,node,outputs,stubs):
    block = node.block
    config = node.config
    coeffs = {}
    for output,stub in zip(outputs,stubs):
        coeffs[output] = stub.coefficient

    # fill missing coefficients with 1.
    for out in block.outputs:
        if not out in coeffs:
            coeffs[out] = 1.0

    # fill in unbound scaling factors.
    scfs={}
    for mode in block.comp_modes:
        if not config.comp_mode is None and \
           not config.comp_mode == mode:
            continue

        scfs[mode] = {}
        for out in block.outputs:
            scfs[mode][out] = block.get_dynamics(mode,out).coefficient()

    # find a computation mode for fanout that fits the negations of the inputs.
    valid_modes = list(get_valid_modes(scfs,coeffs))
    if len(valid_modes) > 0:
        config.set_comp_mode(valid_modes[0])
    else:
        print(scfs,coeffs,stubs)
        #input("=== no valid modes ===")
        print("=== no valid modes ===")

    return len(valid_modes) > 0

def connect_stubs_to_sources(board,node_map,mapping):
    groups = lgraph_util.group_by(mapping, key=lambda args: args[0][0].id)
    succ = True
    for group in groups.values():
        assert(lgraph_util.all_same(map(lambda n: n[0][0].id,\
                                      group)))
        node = group[0][0][0]
        outputs = list(map(lambda args: args[0][1],group))
        stubs = list(map(lambda args: args[1],group))
        for output,input_stub in zip(outputs,stubs):
            input_stub.set_source(node,output)

        if isinstance(node,acirc.ABlockInst):
            succ &= cs2s_blockinst(board,node,outputs,stubs)

        elif isinstance(node,acirc.AJoin):
            cs2s_join(board,node,outputs,stubs)
        else:
            raise Exception("unknown: %s" % node)

    print("=== CONNECTED -> VALIDATING ====")
    for (node,output),inp in mapping:
        in_varmap = \
            any(map(lambda other_node: other_node.contains(inp), \
                    node_map.values()))
        assert(in_varmap)


    return succ

# var_map,source_map
def match_stubs_to_sources(sources,stubs):
    var_choices = {}
    var_sources = {}

    # build data structure for choices
    for var,srcmap in sources.items():
        var_choices[var] = []
        for lvl,srcs in srcmap.items():
            var_sources[(var,lvl)] = []
            for src in srcs:
                var_choices[var].append(lvl)
                var_sources[(var,lvl)].append(src)
    # build final choice and stub maps
    choices = {}
    all_stubs = {}
    for var_name,stubs in stubs.items():
        if not var_name in all_stubs:
            all_stubs[var_name] = []
            choices[var_name] = []

        for stub in stubs:
            selection = []
            for choice in set(var_choices[stub.label]):
                selection.append((stub.label,choice))

            choices[var_name].append(selection)
            all_stubs[var_name].append(stub)

    # go through each choice
    for v in choices:
        for stub,choice in zip(all_stubs[v],choices[v]):
            print(stub,choice)
        print("========")

    def get_level_assignments(var_name,stubs,options):
        for choice in itertools.product(*options):
            outputs = []
            indexes = {}
            invalid = False
            # compute output dictionary
            for var_name,level in choice:
                if not (var_name,level) in indexes:
                    indexes[(var_name,level)] = 0

                idx = indexes[(var_name,level)]
                outs_on_level = var_sources[(var_name,level)]
                if idx >= len(outs_on_level):
                    invalid = True
                    print("%s: in_use=%d level=%d" % (var_name, \
                                                      len(outs_on_level),
                                                      level))
                    break

                out_block,out_port = outs_on_level[idx]
                outputs.append((out_block,out_port))
                indexes[(var_name,level)] += 1

            if not invalid:
                for (outp,port),stub in zip(outputs,stubs):
                    print("%s port=%s :> %s" % (outp.name,port,stub))
                yield list(zip(outputs,stubs))

    assigns = []
    variables = []
    for var_name,choices in choices.items():
        opts = []
        for subassigns in get_level_assignments(var_name,
                                                all_stubs[var_name],
                                                choices):
            opts.append(subassigns)

        if len(opts) == 0:
            print("NO MAPPINGS: %s" % var_name)
            input()
        assigns.append(opts)
        variables.append(var_name)

    for opt in itertools.product(*assigns):
        assignment = []
        for subopt in opt:
            assignment += subopt

        for (out,port),e in assignment:
            print("%s.%s %s" % (out.name,port,e))
        yield assignment



def count_var_refs(frag_node_map):
    refs = dict(map(lambda x : (x,0), frag_node_map.keys()))
    stubs = dict(map(lambda x : (x,[]), frag_node_map.keys()))
    # count how many references
    for var_name,frag in frag_node_map.items():
        for stub in filter(lambda n: isinstance(n,acirc.AInput),
                          frag.nodes()):

            if not stub.label in stubs:
                print("=== stub keys ===")
                for key in stubs:
                    print("  %s" % key)
                raise Exception("<%s> of type <%s> not in stubs" % \
                                (stub.label,stub.__class__.__name__))

            stubs[stub.label].append(stub)
            refs[stub.label] += 1

    return refs,stubs
