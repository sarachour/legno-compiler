import hwlib.block as block
from hwlib.config import Config

class ANode:
    _IDENT = 0;

    class CopyCtx:

        def __init__(self):
            self._map = {}

        def get(self,node):
            if not node.id in self._map:
                for ident in self._map.keys():
                    print(ident)
                print("\nnode: %s" % node)
                raise Exception("<%d> not in copy context [%s]" %\
                                (node.id,node))
            return self._map[node.id]

        def register(self,node,new_node):
            assert(not new_node is None)
            if hash(node) in self._map:
                return False

            new_node._id = node._id
            new_node._namespace = node._namespace
            self._map[node.id] = new_node
            return True

        def copy(self,node):
            if node.id in self._map:
                return self._map[node.id]

            else:
                new_node = node._copy(self)
                if not self.register(node,new_node):
                    return self.get(node)

            nn = self._map[node.id]
            assert(not nn is None)
            if not (str(nn) == str(node)):
                raise Exception("not equal:\n%s\n\n%s\n\n" % (str(nn),str(node)))
            return nn

    def __init__(self):
        self._children = []
        self._parents = []
        self._id = ANode._IDENT
        self._namespace = None
        ANode._IDENT += 1

    @property
    def id(self):
        return self._id

    @property
    def namespace(self):
        assert(not self._namespace is None)
        return self._namespace

    def set_namespace(self,ns):
        assert(not ns is None)
        self._namespace = ns

    def contains(self,n):
        for node in self.nodes():
            if node.id == n.id:
                return True

        return False

    def nodes(self):
        return set(self._nodes())

    def _nodes(self,ids=[]):
        if self.id in ids:
            return

        yield self
        for node in self._children:
            for result in node._nodes(ids+[self.id]):
                yield result

        for node in self._parents:
            for result in node._nodes(ids+[self.id]):
                yield result


    def get_by_id(self,ident):
        for node in self.nodes():
            assert(not node.id is None)
            if ident == node.id:
                return node

        raise Exception("no node with that id")

    def add_child(self,node):
        assert(not node in self._children)
        node._parents.append(self)
        self._children.append(node)

    def add_parent(self,node):
        assert(not node in self._parents)
        self._parents.append(node)
        node._children.append(node)

    def parents(self):
        for par in self._parents:
            yield par

    def children(self):
        for ch in self._children:
            yield ch

    def filter_ancestors(self,fn):
        if fn(self):
            yield self

        for child in self._children:
            for result in child.children(fn):
                yield result

    @staticmethod
    def make_node(board,name,loc=None):
        block = board.block(name)
        node = ABlockInst(block,loc=loc)
        return node

    @staticmethod
    def connect(node1,output,node2,inp):
        assert(not node1 is None)
        assert(not node2 is None)
        conn = AConn(node1,output,node2,inp)

    def subnodes(self):
        raise Exception("produce nodes that are children here")

    def header(self):
        return self.name

    def copy(self):
        engine = ANode.CopyCtx()
        return self._copy(engine),engine

    def __repr__(self):
        return self.to_str(False,prefix='(',delim=' ',postfix=')',indent='')

    def to_str(self,internal_id=False,delim='\n',\
               prefix='',postfix='',indent='  ',printed=[]):
        if self.id in printed:
            return prefix + indent + self.header() +  " {...}" + postfix + delim

        subnodes = list(self.subnodes())
        substr = ""
        for s in subnodes:
            if s.id in printed:
                substr += prefix + indent + s.header() + delim + postfix
            else:
                substr += s.to_str(internal_id,
                                   delim=delim,
                                   prefix=prefix+indent, \
                                   postfix=postfix,
                                   indent=indent,
                                   printed=printed+[self.id])

        ident = "%s." % self._namespace if self._namespace else ""
        ident += "%d." % self._internal_id if internal_id else ""
        return prefix + ident + self.header() + delim + substr + postfix

class AInput(ANode):

    def __init__(self,name,coeff=1.0):
        ANode.__init__(self)
        self._name = name
        self._source = None
        self._coeff = coeff

    def set_source(self,node,output):
        self._source = (node,output)

    @property
    def coefficient(self):
        return self._coeff


    @property
    def label(self):
        return self._name

    @property
    def source(self):
        return self._source

    @property
    def name(self):
        if self._id is None:
            return "%s" % self._name
        else:
            return "%d.%s" % (self._id,self._name)

    def _copy(self,engine):
        node = AInput(self._name,self._coeff)
        success = engine.register(self,node)
        if not success:
            return eng.get(self)

        if not self._source is None:
            old_node,output = self._source
            new_node = engine.copy(old_node)
            node._source = (new_node,output)

        return node

    def header(self):
        if self._source is None:
            return "@%s <= NULL" % self.name
        else:
            return "@%s <= %s.%s" % (self.name,
                                     self._source[0].name,
                                    self._source[1])

    def subnodes(self):
        return []
'''
    def to_str(self,internal_id=False):
        st = ANode.to_str(internal_id)
        if self._source is None:
            st += "@%s <= NULL" % self._name
        else:
            st += "@%s <= %s.%s" % (self._name,
                                     self._source[0].name,
                                    self._source[1])

        return st
'''

class AJoin(ANode):

    def __init__(self):
        ANode.__init__(self)

    @property
    def name(self):
        if self._id is None:
            return "join"
        else:
            return "%d.join" % (self._id)

    def add_parent(self,n):
        assert(not isinstance(n,AJoin))
        ANode.add_parent(self,n)

    def dest(self):
        if len(self._children) == 0:
            return None

        return self._children[0]

    def _copy(self,eng):
        join = AJoin()
        success = eng.register(self,join)
        if not success:
            return eng.get(self)

        for node in self.parents():
            eng.copy(node)

        for node in self.children():
            eng.copy(node)

        return join

    def make(self):
        node = AJoin()
        return node

    def subnodes(self):
        for p in self._parents:
            yield p


    def is_root(self):
        return len(self._children) == 0
'''
    def __repr__(self):
        argstr = " ".join(map(lambda p: str(p),self._parents))
        return "(%s %s)" % (self.name,argstr)
'''

class AConn(ANode):

    def __init__(self,node1,port1,node2,port2):
        ANode.__init__(self)
        self._src_port = port1
        self._dst_port = port2
        self._src_node = None
        self._dst_node = None
        if not node1 is None and not node2 is None:
            self._set_nodes(node1,node2)

    def _set_nodes(self,src_node,dst_node):
        assert(self._src_node is None)
        assert(self._dst_node is None)
        assert(not src_node is None)
        assert(not dst_node is None)
        self._src_node = src_node
        self._dst_node = dst_node
        if isinstance(self._src_node,ABlockInst):
            assert(self._src_port in self._src_node.block.outputs)

        # AJoins may not be on both sides of connections.
        assert(not (isinstance(src_node,AJoin) and \
                    isinstance(dst_node,AJoin)))
        self._src_node.add_child(self)

        if isinstance(self._dst_node,ABlockInst):
            assert(self._dst_port in self._dst_node.block.inputs)

        self.add_child(self._dst_node)

    def _copy(self,eng):
        conn = AConn(None,self._src_port,None,self._dst_port)
        success = eng.register(self,conn)
        if not success:
            eng.get(self)

        src_n = eng.copy(self._src_node)
        dst_n = eng.copy(self._dst_node)
        conn._set_nodes(src_n,dst_n)
        return conn


    @property
    def source(self):
        return self._src_node,self._src_port

    @property
    def dest(self):
        return self._dst_node,self._dst_port

    @property
    def name(self):
        if self._id is None:
            return "conn"
        else:
            return "%d.conn" % (self._id)


    def subnodes(self):
        yield self._src_node

    def header(self):
        return "%s: %s.%s => %s.%s" % (self.name, \
                                       self._src_node.name,
                                       self._src_port,
                                       self._dst_node.name,
                                       self._dst_port)

'''
    def to_str(self,internal_id=False):
        st = ANode.to_str(self,internal_id)
        st += "(%s %s %s %s)" % \
            (self.name,self._dst_port,self._src_port, self._src_node)
        return st
'''


class ABlockInst(ANode):
    def __init__(self,node,loc=None):
        ANode.__init__(self)
        self._block = node
        self._inputs = node.inputs
        self._outputs = node.outputs
        self._loc = loc
        self.config = Config()
        self._used = []

    @property
    def loc(self):
        return self._loc

    @property
    def block(self):
        return self._block

    @property
    def inputs(self):
        return self._inputs

    def _copy(self,eng):
        blk = ABlockInst(self._block)
        blk.config = self.config.copy()
        blk._loc = self._loc
        success = eng.register(self,blk)
        if not success:
            return eng.get(self)

        for par in self.parents():
            eng.copy(par)

        for ch in self.children():
            eng.copy(ch)

        return blk

    @property
    def name(self):
        if self._id is None:
            return "blk %s" % (self._block.name)
        else:
            return "%d.blk %s" % (self._id,self._block.name)

    def get_input_conn(self,inp):
        for conn in self.subnodes():
            dest_node,dest_port = conn.dest
            if dest_node == self and \
               dest_port == inp:
                return conn

        return None

    def use_output(self,output):
        assert(output in self._outputs)
        assert(not output in self._used)
        self._used.append(output)

    def output_used(self,output):
        return output in self._used

    def subnodes(self):
        for par in self._parents:
            yield par

    def header(self):
        return "%s:{%s}" % (self.name,self.config.to_str(","))

'''
    def to_str(self,internal_id=False):
        st = ANode.to_str(self,internal_id)
        argstr = " ".join(map(lambda p: str(p), self._parents))
        st += "(%s {%s} %s)" % (self.name,self.config.to_str(","),argstr)
        return st
'''

class AbsCirc:

    def __init__(self,board):
        self._board = board

    @property
    def board(self):
        return self._board

    @staticmethod
    def count_instances(board,root_nodes):
        counts = dict(map(lambda b: (b.name,0), board.blocks))
        for root_node in root_nodes:
            for node in filter(lambda x : isinstance(x,ABlockInst),
                root_node.nodes()):
                counts[node.block.name] += 1

        return counts

    @staticmethod
    def feasible(board,root_nodes):
        counts = dict(map(lambda b: (b.name,0), board.blocks))
        for root_node in root_nodes:
            for node in filter(lambda x : isinstance(x,ABlockInst),
                root_node.nodes()):
                counts[node.block.name] += 1
                if counts[node.block.name] > \
                   board.num_blocks(node.block.name):
                    return False


        return True
