import compiler.lgraph_pass.route_ilp as route_ilp

def route(board,prob,node_map,max_failures=None,max_resolutions=None):
    #sys.setrecursionlimit(1000)
    ccirc = route_ilp.route(board,prob,node_map)
    if not ccirc is None:
        yield ccirc
