import networkx as nx
from hwlib.block import Block, BlockType

class Layer:

    def __init__(self,board,index,parent=None):
        self._index = index
        self._board = board
        self._parent = parent
        self._layers = {}

    def identifiers(self):
        return self._layers.keys()

    def sublayer(self,pos):
        layer = self.layer(pos[0])
        if len(pos) > 1:
            return layer.sublayer(pos[1:])
        else:
            return layer

    def layer(self,index):
        if (index in self._layers):
            return self._layers[index]

        layer = Layer(self._board,index,parent=self)
        self._layers[index] = layer
        return layer

    @staticmethod
    def from_position_string(position):
        args = position.split("(")[1].split(")")[0].split(",")
        unboxed = []
        for arg in args:
            try:
                unbox_arg = int(arg)
            except Exception as e:
                unbox_arg = arg

            unboxed.append(unbox_arg)

        return unboxed

    @staticmethod
    def _position_string(position):
        return "(%s)" % \
            (",".join(map(lambda idx: str(idx), position)))

    @property
    def position(self):
        pos = [] if self._parent is None else self._parent.position
        pos.append(self._index)
        return pos

    def make_position(self,subpos):
        localpos = [self._index] + subpos if not self._parent is None \
                   else subpos

        return localpos if self._parent is None else \
            self._parent.make_position(localpos)


    @property
    def index(self):
        return self._index


    def is_member(self,sub_pos):
        super_pos = self.position
        assert(len(super_pos) <= len(sub_pos))
        for idx in range(0,len(super_pos)):
            if super_pos[idx] != sub_pos[idx]:
                return False

        return True

    def subpositions(self,recurse=False):
        if len(self._layers) == 0:
            yield [] if not recurse else [self._index]

        for layer in self._layers.values():
            for subp in layer.subpositions(recurse=True):
                yield subp

    def inst(self,block_name):
        return self._board.inst(block_name,self.position)

class Board(Layer):

    CURRENT_MODE = 0
    VOLTAGE_MODE = 1
    MIXED_MODE = 2

    def __init__(self,name,mode):
        Layer.__init__(self,self,name)
        self._name = name
        self._mode = mode
        self._key_to_pos = {}
        self._blocks = {}

        self._time_constant = None
        self._handles = {}

        # accessors
        self._inst_by_block = {}
        self._inst_by_position = {}
        self._inst_to_meta = {}

        # connections
        self._connections = {}
        self._routes = nx.DiGraph()
        self._freeze_insts = False
        self._blacklist = []

    def set_blacklist(self,b):
        self._blacklist = b

    def freeze_instances(self):
        self._freeze_insts =  True

    @property
    def name(self):
        return self._name

    @property
    def blocks(self):
        for block in self._blocks.values():
            yield block

    def block(self,name):
        return self._blocks[name]

    def has_block(self,name):
        return name in self._blocks

    def key_to_loc(self,key):
        return self._key_to_pos[key]

    def num_blocks(self,name):
        return len(self._inst_by_block[name])

    def instances(self):
        for blk,locs in self._inst_by_block.items():
            for loc in locs:
                meta = self._inst_to_meta[(blk,loc)]
                yield blk,loc,meta

    def instances_of_block(self,blk):
        if not blk in self._inst_by_block:
            for oblk in self._inst_by_block.keys():
                logger.info(oblk)
            raise Exception("no instances <%s>" % blk)

        for loc in self._inst_by_block[blk]:
            yield loc

    @property
    def mode(self):
        return self._mode

    def set_time_constant(self,v):
        self._time_constant =v

    @property
    def time_constant(self):
        return self._time_constant

    def add_handle(self,handle,block_name,loc):
        self._handles[handle] = (block_name,loc)

    def handle(self,handle):
        if not handle in self._handles:
            print(self._handles.keys())
            raise Exception("not in handles: <%s>" % handle)
        return self._handles[handle]

    def handles(self):
        for handle,(block,loc) in self._handles.items():
            yield handle,block,loc

    def handle_by_inst(self,block_name,loc):
        for handle,(b,l) in self._handles.items():
            if b == block_name and l == loc:
                return handle
        return None

    def add(self,block_specs):
        for blk in block_specs:
            assert(not blk.name in self._blocks)
            self._blocks[blk.name] = blk

    def block_locs(self,scope,block):
        def is_prefixed(super_l,sub_l):
            assert(len(super_l) <= len(sub_l))
            for idx in range(0,len(super_l)):
                if super_l[idx] != sub_l[idx]:
                    return False

            return True

        if block in self._inst_by_block:
            for lockey in self._inst_by_block[block]:
                loc = self.key_to_loc(lockey)
                if is_prefixed(scope.position,loc):
                    yield self.position_string(loc)

        else:
            return


    def is_block_at(self,block,posstr):
        assert(isinstance(posstr,str))
        if not posstr in self._inst_by_position:
            raise Exception("unknown position: %s" % posstr)

        elif block in self._inst_by_position[posstr]:
            return True

        else:
            return False


    def position_string(self,position):
        assert(not isinstance(position,str))
        if position[0] == self._name:
            posstr = Layer._position_string(position)
        else:
            posstr = Layer._position_string([self._name]+position)

        return posstr


    def route_exists(self,sblk,skey,sport,dblk,dkey,dport):

        if self.can_connect(sblk,skey,sport,dblk,dkey,dport):
            return True

        assert(skey in self._key_to_pos)
        assert(dkey in self._key_to_pos)
        if not self._routes.has_node((sblk,skey,sport)):
            return False

        if not self._routes.has_node((dblk,dkey,dport)):
            return False

        return nx.has_path(self._routes,
                           source=(sblk,skey,sport),
                           target=(dblk,dkey,dport))


    def find_routes(self,sblk,skey,sport,dblk,dkey,dport,count=-1):
        assert(isinstance(skey,str))
        assert(isinstance(dkey,str))

        if self.can_connect(sblk,skey,sport,dblk,dkey,dport):
            yield [(sblk,skey,sport),(dblk,dkey,dport)]

        assert(skey in self._key_to_pos)
        assert(dkey in self._key_to_pos)
        if not self._routes.has_node((sblk,skey,sport)):
            return

        if not self._routes.has_node((dblk,dkey,dport)):
            return

        all_routes = []
        pathgen = nx.all_shortest_paths(self._routes,
                                source=(sblk,skey,sport),
                                target=(dblk,dkey,dport))
        try:
            for path in pathgen:
                if len(all_routes) < count or count < 0:
                    all_routes.append(path)
                else:
                    break

        except nx.NetworkXNoPath as e:
            print("no path: %s[%s].%s->%s[%s].%s" % (sblk,skey,sport, \
                                                     dblk,dkey,dport))
            return

        for route in all_routes:
            yield list(map(lambda args:
                           (args[0],
                            args[1],
                            args[2]),
                           route))


    def inst(self,block_name,_position):
        assert(not self._freeze_insts)
        if (block_name,_position) in self._blacklist:
            return

        if not block_name in self._inst_by_block:
            self._inst_by_block[block_name] = []

        key = self.position_string(_position)
        if not key in self._inst_by_position:
            self._inst_by_position[key] = []

        if(key in self._inst_by_block[block_name]):
            raise Exception("block <%s> already in position <%s>" % \
                            (block_name,key))
        assert(not block_name in self._inst_by_position[key])

        self._key_to_pos[key] = _position
        self._inst_by_block[block_name].append(key)
        self._inst_by_position[key].append(block_name)
        self._inst_to_meta[(block_name,key)] = {}
        block = self.block(block_name)
        if block.type == BlockType.BUS:
            assert(len(block.inputs) == 1)
            assert(len(block.outputs) == 1)

            self._routes.add_node((block_name,key,block.inputs[0]))
            self._routes.add_node((block_name,key,block.outputs[0]))
            self._routes.add_edge((block_name,key,block.inputs[0]),
                                  (block_name,key,block.outputs[0]))

        return key

    def blocks_at(self,key):
        assert(isinstance(key,str))
        for block_name in self._inst_by_position[key]:
            yield self._blocks[block_name]

    def can_connect(self,sblk,skey,sport,dblk,dkey,dport):
        assert(isinstance(skey,str))
        assert(isinstance(dkey,str))
        sblkport = (sblk,sport)
        dblkport = (dblk,dport)
        if not sblkport in self._connections:
            return False

        if not dblkport in self._connections[sblkport]:
            return False

        if not (skey,dkey) in self._connections[sblkport][dblkport]:
            return False

        return True


    def inverts_signal(self,sblk,skey,sport,dblk,dkey,dport):
        assert(isinstance(skey,str))
        assert(isinstance(dkey,str))
        _,_,invert = self._connections[(sblk,sport)][(dblk,dport)][(skey,dkey)]
        return invert

    def connection_list(self):
        for (sblk,sport) in self._connections:
            for (dblk,dport) in self._connections[(sblk,sport)]:
                yield (sblk,sport),(dblk,dport),self._connections[(sblk,sport)][(dblk,dport)]

    def connections(self):
        for (sblk,sport) in self._connections:
            for (dblk,dport) in self._connections[(sblk,sport)]:
                for spos,dpos in self._connections[(sblk,sport)][(dblk,dport)]:
                    yield (sblk,spos,sport),(dblk,dpos,dport)

    def conn(self,sblkname,skey,sport,dblkname,dkey,dport):
        assert(self._freeze_insts)
        assert(isinstance(skey,str))
        assert(isinstance(dkey,str))
        assert(skey in self._key_to_pos)
        assert(dkey in self._key_to_pos)
        if not skey in self._inst_by_block[sblkname]:
            print(self._inst_by_block[sblkname].keys())
            raise Exception("<%s> not in list of defined instances for <%s>"
                            % (skey,sblkname))
        if not dkey in self._inst_by_block[dblkname]:
            print(self._inst_by_block[dblkname].keys())
            raise Exception("<%s> not in list of defined instances for <%s>"
                            % (skey,dblkname))

        if not sblkname in self._blocks:
            print(self._blocks.keys())
            raise Exception("<%s> not in block list" % sblkname)

        if not dblkname in self._blocks:
            print(self._blocks.keys())
            raise Exception("<%s> not in block list" % dblkname)

        sblk = self._blocks[sblkname]
        dblk = self._blocks[dblkname]
        assert(sblk.is_output(sport))
        assert(dblk.is_input(dport))
        sblkport = (sblkname,sport)
        dblkport = (dblkname,dport)

        if not sblkport in self._connections:
            self._connections[sblkport] = {}

        if not dblkport in self._connections[sblkport]:
            self._connections[sblkport][dblkport] = []

        if not (skey,dkey) in self._connections[sblkport][dblkport]:
            self._connections[sblkport][dblkport].append((skey,dkey))

        if not self._routes.has_node((dblkname,dkey,dport)):
            self._routes.add_node((dblkname,dkey,dport))

        if not self._routes.has_node((sblkname,skey,sport)):
            self._routes.add_node((sblkname,skey,sport))

        self._routes.add_edge((sblkname,skey,sport),
                              (dblkname,dkey,dport))
