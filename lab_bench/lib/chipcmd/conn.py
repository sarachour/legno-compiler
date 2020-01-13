import lab_bench.lib.enums as enums
from lab_bench.lib.chipcmd.data import *
from lab_bench.lib.chipcmd.common import *
from lab_bench.lib.base_command import AnalogChipCommand




class ConnectionCmd(AnalogChipCommand):

    def __init__(self,src_blk,src_loc,
                 dst_blk,dst_loc,
                 make_conn=True):
        AnalogChipCommand.__init__(self)
        assert(not src_loc is None and \
               isinstance(src_loc,CircPortLoc))
        self._src_blk = enums.BlockType(src_blk);
        self._src_loc = src_loc;
        self.test_loc(self._src_blk, self._src_loc.loc)
        assert(not src_loc is None and \
               isinstance(dst_loc,CircPortLoc))
        self._dst_blk = enums.BlockType(dst_blk);
        self._dst_loc = dst_loc;
        self.test_loc(self._dst_blk, self._dst_loc.loc)

    def build_ctype(self):
        return {
            'src_blk':self._src_blk.name,
            'src_loc':self._src_loc.build_ctype(),
            'dst_blk':self._dst_blk.name,
            'dst_loc':self._dst_loc.build_ctype()
        }

    def priority(self):
        return Priority.EARLY


    def build_identifier(self,block,ploc,is_input=False):
        rep = "%s %d %d %d" % (block.value,
                               ploc.loc.chip,
                               ploc.loc.tile,
                               ploc.loc.slice)

        if self.specify_index(block,ploc.loc):
            rep += " %d" % ploc.loc.index

        if self.specify_output_port(block) and not is_input:
            rep += " port %d" % ploc.port

        if self.specify_input_port(block) and is_input:
            rep += " port %d" % ploc.port


        return rep

    def __repr__(self):
        return "conn %s.%s <-> %s.%s" % (self._src_blk,
                                         self._src_loc,
                                         self._dst_blk,
                                         self._dst_loc)
class BreakConnCmd(ConnectionCmd):

    def __init__(self,src_blk,src_loc,
                 dst_blk,dst_loc):
        ConnectionCmd.__init__(self,src_blk,src_loc,
                               dst_blk,dst_loc,True)

    def disable(self):
        return self

    @staticmethod
    def name():
        return 'rmconn'

    @staticmethod
    def desc():
        return "make a connection on the hdacv2 board"

    def build_ctype(self):
        data = ConnectionCmd.build_ctype(self)
        return build_circ_ctype({
            'type':enums.CircCmdType.BREAK.name,
            'data':{
                'conn':data
            }
        })


    @staticmethod
    def parse(args):
        result = parse_pattern_conn(args,BreakConnCmd.name())
        if result.success:
            data = result.value
            srcloc = CircPortLoc(data['schip'],data['stile'],
                                 data['sslice'],data['sport'],
                                 data['sindex'])
            dstloc = CircPortLoc(data['dchip'],data['dtile'],
                                 data['dslice'],data['dport'],
                                 data['dindex'])


            return BreakConnCmd(
                data['sblk'],srcloc,
                data['dblk'],dstloc)

        else:
            raise Exception(result.message)


    def __repr__(self):
        src_rep = self.build_identifier(self._src_blk,
                                        self._src_loc,is_input=False)
        dest_rep = self.build_identifier(self._dst_blk,
                                         self._dst_loc,is_input=True)

        return "rmconn %s %s" % (src_rep,dest_rep)





class MakeConnCmd(ConnectionCmd):

    def __init__(self,src_blk,src_loc,
                 dst_blk,dst_loc):
        ConnectionCmd.__init__(self,src_blk,src_loc,
                               dst_blk,dst_loc,True)

    @staticmethod
    def name():
        return 'mkconn'

    @staticmethod
    def desc():
        return "make a connection on the hdacv2 board"

    def priority(self):
        return Priority.LAST

    def build_ctype(self):
        data = ConnectionCmd.build_ctype(self)
        return build_circ_ctype({
            'type':enums.CircCmdType.CONNECT.name,
            'data':{
                'conn':data
            }
        })




    @staticmethod
    def parse(args):
        result = parse_pattern_conn(args,MakeConnCmd.name())
        if result.success:
            data = result.value
            srcloc = CircPortLoc(data['schip'],data['stile'],
                                 data['sslice'],data['sport'],
                                 data['sindex'])
            dstloc = CircPortLoc(data['dchip'],data['dtile'],
                                 data['dslice'],data['dport'],
                                 data['dindex'])


            return MakeConnCmd(
                data['sblk'],srcloc,
                data['dblk'],dstloc)

        else:
            raise Exception(result.message)

    def configure(self):
        return self

    def disable(self):
        return BreakConnCmd(self._src_blk,self._src_loc,
                             self._dst_blk,self._dst_loc)


    def __repr__(self):
        src_rep = self.build_identifier(self._src_blk,
                                        self._src_loc,is_input=False)
        dest_rep = self.build_identifier(self._dst_blk,
                                         self._dst_loc,is_input=True)

        return "mkconn %s %s" % (src_rep,dest_rep)
