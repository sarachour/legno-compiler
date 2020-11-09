import hwlib.adp as adplib
import ops.generic_op as genoplib
import graphviz
from enum import Enum

class Colors:
    LIGHTYELLOW = "#ffeaa7"
    LIGHTPURPLE = "#a29bfe"
    LIGHTGREY = "#ecf0f1"
    LIGHTPINK = "#fd79a8"
    ORANGE = "#e17055"
    BLUE = "#3B3B98"

def render_config_info(board,graph,cfg):
    blk = board.get_block(cfg.inst.block)
    st = []
    st.append("\modes: %s" % (cfg.modes))
    for data in cfg.stmts_of_type(adplib \
                                  .ConfigStmtType \
                                  .CONSTANT):
        st.append("%s=%.2f scf=%.2e" % (data.name, \
                                        data.value, \
                                        data.scf))

    for data in cfg.stmts_of_type(adplib \
                                  .ConfigStmtType \
                                  .EXPR):
        inj_args = dict(map(lambda tup: (tup[0],  \
                                     genoplib.Mult(genoplib.Var(tup[0]), \
                                                   genoplib.Const(tup[1]))), \
                        data.injs.items()))
        subexpr = data.expr.substitute(inj_args)
        st.append("%s=%s injs=%s scfs=%s" \
                  % (data.name,data.expr,data.injs,data.scfs))

    ident = "%s-config" % cfg.inst
    graph.node(ident, "%s" % "\n".join(st), \
               shape="note", \
               style="filled", \
               fillcolor=Colors.LIGHTYELLOW)

    port_id = "%s:block" % (cfg.inst)
    graph.edge(ident,port_id, \
               penwidth="2", \
               style="dashed", \
               arrowhead="tee",
               arrowtail="normal", \
               color=Colors.ORANGE)
    return st


def render_instance(board,graph,cfg,scale=False,source=False):
    def port_text(port):
        text = "%s" % port.name
        if scale:
            text += "\n %.2e" % cfg[port.name].scf
        if source and not cfg[port.name].source is None:
            text += "\n %s" % cfg[port.name].source

        return "<%s> %s" % (port.name,text)

    # render
    blk = board.get_block(cfg.inst.block)
    block_templ= "{inputs} |<block> {block_info}| {outputs}"
    inputs = []
    outputs = []
    graph.attr(shape='record')
    for inp in blk.inputs:
        inputs.append(port_text(inp))

    for out in blk.outputs:
        outputs.append(port_text(out))

    block_name = str(cfg.inst)
    block_text = block_templ.format(
        block_info=str(cfg.inst),
        inputs= "{%s}" % ("|".join(inputs)),
        outputs="{%s}" % ("|".join(outputs))
    )
    graph.node(block_name, "{%s}" % block_text, \
               shape="record", \
               style="filled", \
               fillcolor=Colors.LIGHTGREY)

def render_port_scf(board,graph,inst,stmt):
    source_templ = "{port} scf={scf:.2f}"
    source_text = source_templ.format(
        scf=stmt.scf, \
        port=stmt.name
    )
    source_id = "%s-%s-scf" % (inst,stmt.name)
    graph.node(source_id, source_text, \
               shape="trapezium", \
               style="filled", \
               fillcolor=Colors.LIGHTPURPLE)

    port_id = "%s:%s" % (inst,stmt.name)
    graph.edge(source_id,port_id)

def render_source_label(board,graph,inst,stmt):
    source_templ = "expr={dsexpr} scf={scf:.2f}"
    source_id = "%s-%s-%s" % (inst,stmt.name,stmt.source)
    source_text = source_templ.format(
        dsexpr=stmt.source, \
        scf=stmt.scf \
    )
    graph.node(source_id, source_text, \
               shape="cds", \
               style="filled", \
               fillcolor=Colors.LIGHTPINK)

    port_id = "%s:%s" % (inst,stmt.name)
    graph.edge(source_id,port_id)

def render_conn(graph,conn):
    src_id = "%s:%s" % (conn.source_inst,conn.source_port)
    dest_id = "%s:%s" % (conn.dest_inst,conn.dest_port)
    graph.edge(src_id,dest_id, \
               penwidth="4", \
               arrowhead="box",
               arrowtail="normal", \
               color=Colors.BLUE)

def render(board,adp,filename):
    print(graphviz.version())
    graph = graphviz.Digraph('adp-viz', \
                           filename=filename, \
                           graph_attr={
                               "overlap":'false',
                               "splines":'true', \
                           })
    for cfg in adp.configs:
        render_instance(board,graph,cfg,scale=True,source=True)
        render_config_info(board,graph,cfg)

        #for stmt in cfg.stmts_of_type(adplib.ConfigStmtType.PORT):
            #if not stmt.source is None:
            #    render_source_label(board,graph,cfg.inst,stmt)
            #else:
                #render_port_scf(board,graph,cfg.inst,stmt)

    for conn in adp.conns:
        render_conn(graph,conn)

    graph.render()
