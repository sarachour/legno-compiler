import hwlib.adp as adplib
import ops.generic_op as genoplib
import graphviz
from enum import Enum

class Colors:
    LIGHTYELLOW = "#ffeaa7"
    LIGHTPURPLE = "#a29bfe"
    LIGHTGREY = "#ecf0f1"
    LIGHTPINK="#f8a5c2"
    LIGHTCYAN="#9AECDB"

    PINK = "#fd79a8"
    ORANGE = "#e17055"
    BLUE = "#3B3B98"
    PURPLE= "#B53471"
    CYAN = "#12CBC4"

def render_config_info(board,graph,cfg):
    blk = board.get_block(cfg.inst.block)
    mode_st = []
    df_st = []
    lb_st = []
    for mode in cfg.modes:
        mode_st.append("%s" % (mode))

    for data in cfg.stmts_of_type(adplib \
                                  .ConfigStmtType \
                                  .CONSTANT):
        if not data.value is None:
            df_st.append("%s=%.2f" % (data.name, data.value))
        else:
            assert(not data.label is None)
            df_st.append("%s=%s" % (data.name, data.label.pretty_print()))

    for data in cfg.stmts_of_type(adplib \
                                  .ConfigStmtType \
                                  .EXPR):
        inj_args = dict(map(lambda tup: (tup[0],  \
                                     genoplib.Mult(genoplib.Var(tup[0]), \
                                                   genoplib.Const(tup[1]))), \
                        data.injs.items()))
        subexpr = data.expr.substitute(inj_args)
        df_st.append("%s=%s" \
                  % (data.name,data.expr.pretty_print()))

    label_groups = {}
    for port in cfg.stmts_of_type(adplib \
                                  .ConfigStmtType \
                                  .PORT):
        if not port.source is None:
            pretty_expr = port.source.pretty_print()
            if not pretty_expr in label_groups:
                label_groups[pretty_expr] = []
            label_groups[pretty_expr].append(port.name)

    for expr,ports in label_groups.items():
        lhs = ",".join(ports)
        lb_st.append("%s=%s" % (lhs,expr))

    st = []
    st.append("[modes]")
    st += mode_st
    if len(df_st) > 0:
        st.append("[data]")
        st += df_st
    if len(lb_st) > 0:
        st.append("[labels]")
        st += lb_st


    ident = "%s-config" % cfg.inst
    graph.node(ident, "%s" % "\l".join(st), \
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


def render_time_constant(graph,tau):
    ident = "time-constant"
    graph.node(ident, "time scale factor\n%.3f" % tau, \
               shape="note", \
               style="filled", \
               fillcolor=Colors.LIGHTPINK)

def render_scale_xform_info(board,graph,cfg):
    groupings = {}
    def add(name,scf):
        scf_fmt = "%.3f" % scf
        if not scf_fmt in groupings:
            groupings[scf_fmt] = []

        groupings[scf_fmt].append(name)

    blk = board.get_block(cfg.inst.block)
    for data in cfg.stmts_of_type(adplib \
                                  .ConfigStmtType \
                                  .CONSTANT):
        add(data.name,data.scf)

    for data in cfg.stmts_of_type(adplib \
                                  .ConfigStmtType \
                                  .EXPR):
        add(data.name,data.scfs[data.name])

    for port in cfg.stmts_of_type(adplib \
                                  .ConfigStmtType \
                                  .PORT):
        add(port.name,port.scf)


    st = []
    for value,names in groupings.items():
        lhs = ",".join(names)
        st.append("%s=%s" % (lhs,value))

    ident = "%s-xform" % cfg.inst
    graph.node(ident, "%s" % "\n".join(st), \
               shape="note", \
               style="filled", \
               fillcolor=Colors.LIGHTCYAN)

    port_id = "%s:block" % (cfg.inst)
    graph.edge(ident,port_id, \
               penwidth="2", \
               style="dashed", \
               arrowhead="tee",
               arrowtail="normal", \
               color=Colors.CYAN)
    return st


def render_instance(board,graph,cfg):
    def port_text(port):
        text = "%s" % port.name
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
    source_templ = "{port}"
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
    source_templ = "expr={dsexpr}"
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

def render(board,adp,filename,scale_transform=True):
    print(graphviz.version())
    graph = graphviz.Digraph('adp-viz', \
                           filename=filename, \
                           graph_attr={
                               "overlap":'false',
                               "splines":'true', \
                           })
    for cfg in adp.configs:
        render_instance(board,graph,cfg)
        render_config_info(board,graph,cfg)
        if scale_transform:
            render_scale_xform_info(board,graph,cfg)

    for conn in adp.conns:
        render_conn(graph,conn)

    if scale_transform:
        render_time_constant(graph,adp.tau)

    graph.render(format="png")
