from hwlib.config import Config, Labels
import json
import os
import hwlib.adp_graphlib as graphlib

class AnalogDeviceProg:

    def __init__(self,board,filename=None):
        self._board = board
        self._tau = 1.0
        self._configs= {}
        self._conns = {}
        self._filename = filename
        #self._intervals = {}
        #self._bandwidths = {}
        self.meta = {}

    def copy(self):
        circ = AnalogDeviceProg(self._board)
        circ.set_tau(self.tau)
        for block_name,loc,cfg in self.instances():
            circ.use(block_name,loc,cfg.copy())

        for sb,sl,sp,db,dl,dp in self.conns():
            circ.conn(sb,sl,sp,db,dl,dp)

        return circ

    def set_tau(self,value):
        self._tau = value

    @property
    def filename(self):
        return self._filename


    @property
    def tau(self):
        return self._tau

    @property
    def board(self):
        return self._board

    def instances_of_block(self,block_name):
        if not block_name in self._configs:
            return

        for loc,config in self._configs[block_name].items():
            yield loc,config

    def instances(self):
        for block_name in self._configs:
            for loc,config in \
                self._configs[block_name].items():
                yield block_name,loc,config


    def use(self,block,loc,config=None):
        if not self._board is None and\
           not self._board.is_block_at(block,loc):
            for block in self._board.blocks_at(loc):
                print(block.name)
            raise Exception("no block <%s> at location <%s>." \
                            % (block.name,loc))

        if not block in self._configs:
            self._configs[block] = {}

        assert(isinstance(loc,str))
        if loc in self._configs[block]:
            if not (config is None):
                raise Exception("location with config already in system: <%s:%s>" % \
                                (block,loc))
            return

        config = Config() if config is None else config
        self._configs[block][loc] = config
        addr = (block,loc)

    def in_use(self,block_name,loc):
        if not block_name in self._configs:
            return False

        if not loc in self._configs[block_name]:
            return False

        return True

    def get_conns_by_src(self,tblk,tloc,tport):
        assert(isinstance(tblk,str))
        assert(isinstance(tloc,str))
        assert(isinstance(tport,str))
        if not (tblk,tloc,tport) in self._conns:
            return []
        else:
            tup = self._conns[(tblk,tloc,tport)]
            return [tup]

    def get_conns_by_dest(self,tblk,tloc,tport):
        assert(isinstance(tblk,str))
        assert(isinstance(tloc,str))
        assert(isinstance(tport,str))
        for (sblock,sloc,sport), \
            (dblock,dloc,dport) in self._conns.items():
            if tblk != dblock or tloc != dloc or tport != dport:
                continue

            yield sblock,sloc,sport


    def has_physical_model(self):
        for _,_,config in self.instances():
            if not config.has_physical_model():
                return False

        return True

    def conns_by_dest(self):
        srcs = {}
        for (sblock,sloc,sport), \
            (dblock,dloc,dport) in self._conns.items():
            if not (dblock,dloc,dport) in srcs:
                srcs[(dblock,dloc,dport)] = []

            srcs[(dblock,dloc,dport)].append((sblock,sloc,sport))


        for (dblock,dloc,dport),src_list in srcs.items():
            yield dblock,dloc,dport,src_list

    def conns(self):
        for (sblock,sloc,sport), \
            (dblock,dloc,dport) in self._conns.items():
            yield sblock,sloc,sport,dblock,dloc,dport

    def has_conn(self,block1,loc1,port1,block2,loc2,port2):
        return self._board.can_connect(block1,loc1,port1,
                                       block1,loc2,port2)


    def find_routes(self,block1,loc1,port1,block2,loc2,port2):
        for path in self._board.find_routes(block1,loc1,port1,
                                            block2,loc2,port2):
            yield path


    def conn(self,block1,loc1,port1,block2,loc2,port2,check_conn=False):
        if not self.in_use(block1,loc1):
            raise Exception("block <%s.%s> not in use" % (block1,loc1))

        if not self.in_use(block2,loc2):
            raise Exception("block <%s.%s> not in use" % (block1,loc1))


        if check_conn and \
           not self._board is None and \
           not self._board.can_connect(block1,loc1,port1,
                                       block2,loc2,port2):
            raise Exception("cannot connect <%s.%s.%s> to <%s.%s.%s>" % \
                            (block1,loc1,port1,block2,loc2,port2))


        assert(not (block1,loc1,port1) in self._conns)

        self._conns[(block1,loc1,port1)] = (block2,loc2,port2)


    def config(self,block,loc):
        return self._configs[block][loc]

    def check(self):
        return self

    @staticmethod
    def from_json(board,obj):
        circ = AnalogDeviceProg(board)
        circ.set_tau(obj['tau'])
        for inst in obj['insts']:
            assert(board is None or \
                   inst['board'] == board.name)
            config = Config.from_json(inst['config'])
            block,loc = inst['block'],inst['loc']
            circ.use(block,loc,config)

        for conn in obj['conns']:
            dest_obj = conn['dest']
            src_obj = conn['source']

            dblk = dest_obj['block']
            dport = dest_obj['port']
            dloc = dest_obj['loc']

            sblk = src_obj['block']
            sport = src_obj['port']
            sloc = src_obj['loc']

            circ.conn(sblk,sloc,sport, \
                      dblk,dloc,dport)

        return circ

    @staticmethod
    def read(board,filename):
        with open(filename,'r') as fh:
            obj = json.loads(fh.read())
            adp = AnalogDeviceProg.from_json(board,obj)
            adp._filename = filename
            return adp

    def to_json(self):
        data_struct = {
            'tau': self._tau,
            'insts': [],
            'conns':[],
            'intervals':{},
            'bandwidths':{}
        }

        for block,locs in self._configs.items():
            for loc,cfg in locs.items():
                inst = {'block':block,'loc':loc, \
                        'board':self._board.name}
                inst['config'] = cfg.to_json()
                data_struct['insts'].append(inst)

        for (src_block,src_loc,src_port), \
            (dst_block,dst_loc,dst_port) in self._conns.items():
            conn = {
                'source':{'block':src_block,'loc':src_loc,'port':src_port},
                'dest':{'block':dst_block,'loc':dst_loc,'port':dst_port}
            }
            data_struct['conns'].append(conn)

        return data_struct

    def write_circuit(self,filename):
        data = self.to_json()
        with open(filename,'w') as fh:
            strdata = json.dumps(data,indent=4)
            fh.write(strdata)


    def write_graph(self,filename,
                    color_method=None,
                    write_png=False):
        graphlib.write_graph(self,filename, \
                             color_method, \
                             write_png)


