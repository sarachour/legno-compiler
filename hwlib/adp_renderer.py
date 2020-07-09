import graphviz

def render_config(board,graph,cfg):
    # render
    blk = board.get_block(cfg.inst.block)
    block_templ= "{inputs} |<block> {block_info}| {outputs}"
    inputs = []
    outputs = []
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
    graph.node(block_name, "{%s}" % block_text,
    {'shape':'record'})



def render(board,adp,filename):
    print(filename)
    graph = graphviz.Graph('adp-viz', filename=filename, engine='fdp')
    for cfg in adp.configs:
        render_config(board,graph,cfg)

    for conn in adp.conns:
        src_id = "%s:block" % (conn.source_inst)
        dest_id = "%s:block" % (conn.dest_inst)
        print(src_id)
        print(dest_id)
        graph.edge(src_id,dest_id)

    graph.render()
