import lab_bench.lib.cstructs as cstructs
import lab_bench.lib.util as util
import time
import lab_bench.lib.enums as enums
from enum import Enum
import re
import math

class OptionalValue:

    def __init__(self,value,success=True):
        self.value = value
        self.success = success

    @property
    def message(self):
        assert(not self.success)
        return self.value

    @staticmethod
    def error(msg):
        return OptionalValue(msg,success=False)

    @staticmethod
    def value(val):
        return OptionalValue(val,success=True)

class Command:
    # debug =1 : don't run me
    def __init__(self):
        self._success = True
        self._msg = None

    def fail(self,msg):
        self._msg = msg
        self._success = False

    def test(self):
        return self._success

    def error_msg(self):
        return self._msg


    def execute(self,state,kwargs={}):
        if self._success:
            return self.execute_command(state,**kwargs)
        else:
            print("[error]" % self._msg)

        return None

    def tostr(self):
        raise NotImplementedError

class ArduinoResponseType(Enum):
    PROCESS = "process"
    DEBUG = "debug"
    DONE = "done"
    DATA = "data"
    ERROR = "error"
    PAYLOAD = "array"
    MESSAGE = "msg"
    RESPONSE = "resp"

class ArduinoResponseState(Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    WAITFOR_DATA = "waitfor-data"
    WAITFOR_PAYLOAD = "waitfor-payload"


class ArduinoResponseDataType(Enum):
    FLOAT = "f"
    FLOATARRAY = "F"
    INT = "i"


class GenericArduinoResponse:

    def __init__(self,type_):
        self._type = type_

    @property
    def type(self):
        return self._type

    def __repr__(self):
        return "generic-resp(%s)" % str(self.type.value)

class ErrorArduinoResponse(GenericArduinoResponse):

    def __init__(self,msg):
        GenericArduinoResponse.__init__(self,ArduinoResponseType.ERROR)
        self._msg = msg

    @property
    def message(self):
        return self._msg

    def __repr__(self):
        return "message-resp(%s)" % \
            (self._msg)

    @staticmethod
    def parse(args):
        msg = args[0]
        return ErrorArduinoResponse(msg)


class MessageArduinoResponse(GenericArduinoResponse):

    def __init__(self,msg):
        GenericArduinoResponse.__init__(self,ArduinoResponseType.MESSAGE)
        self._msg = msg

    @property
    def message(self):
        return self._msg

    def __repr__(self):
        return "message-resp(%s)" % \
            (self._msg)

    @staticmethod
    def parse(args):
        if len(args) == 0:
            raise Exception("can't parse: returned <%s>" % args)
        msg = args[0]
        return MessageArduinoResponse(msg)



class HeaderArduinoResponse(GenericArduinoResponse):

    def __init__(self,msg,n_args):
        GenericArduinoResponse.__init__(self,ArduinoResponseType.RESPONSE)
        self._msg = msg
        self._n = n_args
        self._args = [None]*n_args

    def done(self):
        for arg in self._args:
            if arg is None:
                return False
        return True

    def set_data(self,idx,arg):
        assert(idx < self._n)
        self._args[idx] = arg

    @property
    def message(self):
        return self._msg

    def data(self,i):
        return self._args[i]

    @staticmethod
    def parse(args):
        n = int(args[0])
        msg = args[1]
        return HeaderArduinoResponse(msg,n)

    def __repr__(self):
        return "header-resp(%s,%d) {%s}" % \
            (self._msg,self._n,self._args)

class DataArduinoResponse(GenericArduinoResponse):

    def __init__(self,value,size=1,type=float):
        GenericArduinoResponse.__init__(self,ArduinoResponseType.DATA)
        self._size = size
        self._datatype = type
        self._value = None
        self.set_value(value)

    @property
    def value(self):
        return self._value

    def set_value(self,v):
        if not v is None:
            if not self.is_array():
                self._value = self._datatype(v)
            else:
                self._value = list(map(lambda el: \
                                       self._datatype(el), v))

    def is_array(self):
        return self._size > 1

    @staticmethod
    def parse(args):
        typ = args[0]
        if typ == 'i':
            return DataArduinoResponse(int(args[1]), \
                                       type=int)
        elif typ == 'f':
            return DataArduinoResponse(float(args[1]), \
                                       type=float)
        elif typ == 'I':
            return DataArduinoResponse(None,size=int(args[1]), \
                                       type=int)
        elif typ == 'F':
            return DataArduinoResponse(None,size=int(args[1]), \
                                       type=float)
        else:
            raise Exception("unimpl: %s" % str(args))

    def __repr__(self):
        return "data-resp(%s)" % str(self.type.value)




class PayloadArduinoResponse(GenericArduinoResponse):

    def __init__(self,n):
        GenericArduinoResponse.__init__(self,ArduinoResponseType.PAYLOAD)
        self._array = None
        self._n = n

    @property
    def array(self):
        return self._array

    @property
    def n(self):
        return self._n

    def set_array(self,data):
        assert(len(data) == self._n)
        self._array = data

    @staticmethod
    def parse(args):
        values = args[0].strip().split()
        resp = PayloadArduinoResponse(len(values))
        buf = [0.0]*len(values)
        for idx,val in enumerate(values):
            buf[idx] = float(val)
        resp.set_array(buf)
        return resp


    def __repr__(self):
        return "payload-resp(%s,n=%d)" % (str(self._array),self._n)


class ArduinoCommand(Command):
    HEADER = "AC:>"
    # 1=only print commands
    # 0=run commands
    DEBUG = 0

    @staticmethod
    def set_debug(debug):
        if debug:
            ArduinoCommand.DEBUG = 1
        else:
            ArduinoCommand.DEBUG = 0

    def __init__(self,typ=cstructs.cmd_t()):
        Command.__init__(self)
        self._c_type = typ

    def build_dtype(self,rawbuf):
        raise NotImplementedError

    def build_ctype(self,offset,n):
        raise NotImplementedError


    @staticmethod
    def parse_response(msg):
        rest = msg.strip().split(ArduinoCommand.HEADER)[1]
        args = list(filter(lambda tok: len(tok) > 0, \
                           re.split("[\]\[]+",rest)))
        typ = ArduinoResponseType(args[0])
        if typ == ArduinoResponseType.RESPONSE:
            return HeaderArduinoResponse.parse(args[1:])

        if typ == ArduinoResponseType.MESSAGE:
            return MessageArduinoResponse.parse(args[1:])

        elif typ == ArduinoResponseType.DATA:
            return DataArduinoResponse.parse(args[1:])

        elif typ == ArduinoResponseType.PAYLOAD:
            return PayloadArduinoResponse.parse(args[1:])

        elif typ == ArduinoResponseType.ERROR:
            return ErrorArduinoResponse.parse(args[1:])
        else:
            return GenericArduinoResponse(typ)

    @staticmethod
    def is_response(msg):
        return msg.startswith(ArduinoCommand.HEADER)

    def get_response(self,st):
        ard = st.arduino
        state = ArduinoResponseState.PENDING
        this_resp = None
        this_data = None
        data_idx = 0

        while True:
            line = ard.readline()
            if self.is_response(line):
                resp = self.parse_response(line)
                if resp.type == ArduinoResponseType.PROCESS:
                    if not (state == ArduinoResponseState.PENDING):
                        raise Exception("expected pending, received <%s>" % resp)
                    state = ArduinoResponseState.PROCESSED

                elif resp.type == ArduinoResponseType.RESPONSE:
                    assert(state == ArduinoResponseState.PROCESSED)
                    state = ArduinoResponseState.WAITFOR_DATA
                    this_resp = resp
                    if this_resp.done():
                        return this_resp

                elif resp.type == ArduinoResponseType.DATA:
                    if resp.is_array():
                        this_data = resp
                        state = ArduinoResponseState.WAITFOR_PAYLOAD
                    else:
                        this_resp.set_data(data_idx, resp.value)
                        data_idx += 1

                    if this_resp.done():
                        return this_resp

                elif resp.type == ArduinoResponseType.PAYLOAD:
                    assert(state == ArduinoResponseState.WAITFOR_PAYLOAD)
                    this_data.set_value(resp.array)
                    this_resp.set_data(data_idx, this_data.value)
                    data_idx += 1
                    this_data = None
                    state = ArduinoResponseState.WAITFOR_DATA

                    if this_resp.done():
                        return this_resp

                elif resp.type == ArduinoResponseType.MESSAGE:
                    print("[msg] %s" % resp.message)
                    if "ERROR:" in line:
                        print("ERROR DETECTED..QUITTING...")
                        ard.close()
                        sys.exit(1)

                elif resp.type == ArduinoResponseType.DONE:
                    print("<simulation finished>")
                    continue

                elif resp.type == ArduinoResponseType.ERROR:
                    raise Exception(resp.message)

                else:
                    raise Exception("unhandled: %s" % line)



    def try_waitfor(self,st,type_):
        ard = st.arduino
        while True:
            line = ard.try_readline()
            #print("try_waitfor[%s]> %s" % (type_.value,line))
            if line is None:
                return False

            if self.is_response(line):
                resp = self.parse_response(line)
                if resp.type == type_:
                    return True

    def waitfor(self,st,type_):
        ard = st.arduino
        while True:
            line = ard.readline()
            #print("waitfor[%s]> %s" % (type_.value,line))
            if self.is_response(line):
                resp = self.parse_response(line)
                if resp.type == type_:
                    return True


    def write_to_arduino(self,state,cdata):
        if not state.dummy:
            #print("execute: %s [%d]" % (self,len(cdata)))
            # twenty bytes
            state.arduino.write_bytes(cdata)
            state.arduino.write_newline()
            resp = self.get_response(state)
            return resp

        return None

    def execute_command(self,state,raw_data=None,n_data_bytes=1000,elem_size=4):
        if state.dummy:
            return None

        def construct_bytes(offset=None,n=None):
            if not raw_data is None:
                header_type= self.build_ctype(offset=offset,n=n)
                header_data = self._c_type.build(header_type)
                # pad to fill up rest of struct before tacking on data.
                pad_size= 80
                n_pad = util.compute_pad_bytes(len(header_data),pad_size)
                pad_data = bytearray([0]*n_pad)
                # data
                chunk = raw_data[offset:offset+n]
                body_type = self.build_dtype(chunk)
                body_data = body_type.build(chunk)
                rawbuf = header_data+pad_data+body_data

            else:
                header_type= self.build_ctype()
                header_data = self._c_type.build(header_type)
                rawbuf = header_data

            return rawbuf

        if not raw_data is None:
            chunk_size = math.floor(n_data_bytes/elem_size)
            offset = 0
            n_els = len(raw_data)
            resps = []
            while offset < n_els:
                n = chunk_size if n_els-offset >= chunk_size \
                    else n_els-offset
                rawbuf = construct_bytes(offset,n)
                resp = self.write_to_arduino(state,rawbuf)
                resps.append(resp)
                offset += n
            return resps

        else:
            rawbuf = construct_bytes()
            resp = self.write_to_arduino(state,rawbuf)
            return resp

        return None


class FlushCommand(ArduinoCommand):
    def __init__(self):
        ArduinoCommand.__init__(self);

    def build_ctype(self):
        return {
            'test':ArduinoCommand.DEBUG,
            'type':enums.CmdType.FLUSH_CMD.name,
            'data': {
                'flush_cmd':255
            }
        }

    def execute_command(self,state):
        ArduinoCommand.execute_command(self,state)
        return True

    def __repr__(self):
        return "flush"




class AnalogChipCommand(ArduinoCommand):

    def __init__(self):
        ArduinoCommand.__init__(self,cstructs.cmd_t())

    def specify_index(self,block,loc):
        return (block == enums.BlockType.FANOUT) \
            or (block == enums.BlockType.TILE_INPUT) \
            or (block == enums.BlockType.TILE_OUTPUT) \
            or (block == enums.BlockType.MULT)

    def specify_output_port(self,block):
        return (block == enums.BlockType.FANOUT)

    def specify_input_port(self,block):
        return (block == enums.BlockType.MULT)

    def test_loc(self,block,loc):
        NCHIPS = 2
        NTILES = 4
        NSLICES = 4
        NINDICES_COMP = 2
        NINDICES_TILE = 4
        if not loc.chip in range(0,NCHIPS):
            self.fail("unknown chip <%d>" % loc.chip)
        if not loc.tile in range(0,NTILES):
            self.fail("unknown tile <%d>" % loc.tile)
        if not loc.slice in range(0,NSLICES):
            self.fail("unknown slice <%d>" % loc.slice)

        if (block == enums.BlockType.FANOUT) \
            or (block == enums.BlockType.TILE_INPUT) \
            or (block == enums.BlockType.TILE_OUTPUT) \
            or (block == enums.BlockType.MULT):
            indices = {
                enums.BlockType.FANOUT: range(0,NINDICES_COMP),
                enums.BlockType.MULT: range(0,NINDICES_COMP),
                enums.BlockType.TILE_INPUT: range(0,NINDICES_TILE),
                enums.BlockType.TILE_OUTPUT: range(0,NINDICES_TILE)
            }
            if loc.index is None:
                self.fail("expected index <%s>" % block)

            elif not loc.index in indices[block]:
                self.fail("block <%s> index <%d> must be from indices <%s>" %\
                          (block,loc.index,indices[block]))

        elif not block is None:
           if not (loc.index is None or loc.index == 0):
               self.fail("expected no index <%s> <%d>" %\
                         (block,loc.index))

        else:
            self.fail("not in block list <%s>" % block)

