import graphviz
import compiler.lgraph_pass.vadp as vadplib


def render_config(graph, stmt):
    # render
    blk = stmt.block
    block_templ = "{inputs} |<block> {block_info}| {outputs}"
    inputs = []
    outputs = []
    graph.attr(shape='record')
    for inp in blk.inputs:
        inputs.append("<%s> %s" % (inp.name, inp.name))

    for out in blk.outputs:
        outputs.append("<%s> %s" % (out.name, out.name))

    block_name = "%s%s" % (stmt.block.name,stmt.ident)
    block_text = block_templ.format(block_info="%s %s" % (blk.name,stmt.ident),
                                    inputs="{%s}" % ("|".join(inputs)),
                                    outputs="{%s}" % ("|".join(outputs)))
    graph.node(block_name, "{%s}" % block_text)

    return
    graph.attr(shape='point')
    for port in list(blk.inputs) + list(blk.outputs):
        port_id = "%s:%s:%s" % (block_name, stmt.ident, port.name)
        port_name = "%s-port-%s" % (block_name, port.name)
        graph.node(port_name, port.name)
        if port in blk.inputs:
            graph.edge(port_name, port_id)
        else:
            graph.edge(port_id, port_name)

def render(vadp, filename):
    print(graphviz.version())
    graph = graphviz.Digraph('vadp-viz', \
                           filename=filename, \
                           graph_attr={
                               "overlap":'scale', \
                               "nodesep":'1', \
                               "splines":'curved', \
                           },
                           node_attr={'shape':'record'})
    for idx,stmt in enumerate(vadp):
        if isinstance(stmt, vadplib.VADPConfig):
            render_config(graph, stmt)

        elif isinstance(stmt, vadplib.VADPConn):
          src_id = "%s%s:%s" % (stmt.source.block.name, stmt.source.ident, stmt.source.port.name)
          sink_id = "%s%s:%s" % (stmt.sink.block.name, stmt.sink.ident , stmt.sink.port.name)
          graph.edge(src_id, sink_id)

        elif isinstance(stmt,vadplib.VADPSink):
          port_id = "%s%s:%s" % (stmt.port.block.name, stmt.port.ident, stmt.port.port.name)
          sink_id = "sink%d" % idx
          graph.node(sink_id, "sink:" + str(stmt.dsexpr))
          graph.edge(sink_id,port_id)

        elif isinstance(stmt,vadplib.VADPSource):
          port_id = "%s%s:%s" % (stmt.port.block.name, stmt.port.ident, stmt.port.port.name)
          source_id = "src%d" % idx
          graph.node(source_id, "source: "+str(stmt.dsexpr))
          graph.edge(port_id,source_id)

    graph.render()
