import graphviz

def render_config(board,graph,cfg):
    # render
    blk = board.get_block(cfg.inst.block)
    block_templ= "{inputs} |<block> {block_info}| {outputs}"
    inputs = []
    outputs = []
    graph.attr(shape='record')
    for inp in blk.inputs:
        inputs.append("<%s> %s" % (inp.name,inp.name))

    for out in blk.outputs:
        outputs.append("<%s> %s" % (out.name,out.name))

    block_name = str(cfg.inst)
    block_text = block_templ.format(
        block_info=str(cfg.inst),
        inputs= "{%s}" % ("|".join(inputs)),
        outputs="{%s}" % ("|".join(outputs))
    )
    graph.node(block_name, "{%s}" % block_text)

def render(board,adp,filename):
    print(graphviz.version())
    graph = graphviz.Digraph('adp-viz', \
                           filename=filename, \
                           graph_attr={
                               "overlap":'scale', \
                               "nodesep":'1', \
                               "splines":'curved', \
                           },
                           node_attr={'shape':'record'})
    for cfg in adp.configs:
        render_config(board,graph,cfg)

    for conn in adp.conns:
        src_id = "%s:%s" % (conn.source_inst,conn.source_port)
        dest_id = "%s:%s" % (conn.dest_inst,conn.dest_port)
        graph.edge(src_id,dest_id)

    graph.render()
