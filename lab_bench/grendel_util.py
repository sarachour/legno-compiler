import re
import math
from enum import Enum
import sys

class OptionalValue:
  def __init__(self, value, success=True):
    self.value = value
    self.success = success

  @property
  def message(self):
    assert (not self.success)
    return self.value

  @staticmethod
  def error(msg):
    return OptionalValue(msg, success=False)

  @staticmethod
  def value(val):
    return OptionalValue(val, success=True)


class Command:
  # debug =1 : don't run me
  def __init__(self):
    self._success = True
    self._msg = None

  def fail(self, msg):
    self._msg = msg
    self._success = False

  def test(self):
    return self._success

  def error_msg(self):
    return self._msg

  def execute(self, state, kwargs={}):
    if self._success:
      return self.execute_command(state, **kwargs)
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
  def __init__(self, type_):
    self._type = type_

  @property
  def type(self):
    return self._type

  def __repr__(self):
    return "generic-resp(%s)" % str(self.type.value)


class ErrorArduinoResponse(GenericArduinoResponse):
  def __init__(self, msg):
    GenericArduinoResponse.__init__(self, ArduinoResponseType.ERROR)
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
  def __init__(self, msg):
    GenericArduinoResponse.__init__(self, ArduinoResponseType.MESSAGE)
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
  def __init__(self, msg, n_args):
    GenericArduinoResponse.__init__(self, ArduinoResponseType.RESPONSE)
    self._msg = msg
    self._n = n_args
    self._args = [None] * n_args

  def done(self):
    for arg in self._args:
      if arg is None:
        return False
    return True

  @property
  def num_args(self):
    return self._n

  def set_data(self, idx, arg):
    assert (idx < self._n)
    self._args[idx] = arg

  @property
  def message(self):
    return self._msg

  def data(self, i):
    return self._args[i]

  @staticmethod
  def parse(args):
    n = int(args[0])
    msg = args[1]
    return HeaderArduinoResponse(msg, n)

  def __repr__(self):
    return "header-resp(%s,%d) {%s}" % \
        (self._msg,self._n,self._args)


class DataArduinoResponse(GenericArduinoResponse):
  def __init__(self, value, size=1, type=float):
    GenericArduinoResponse.__init__(self, ArduinoResponseType.DATA)
    self._size = size
    self._datatype = type
    self._value = None
    self.set_value(value)

  @property
  def value(self):
    return self._value

  def set_value(self, v):
    self._value = v

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
    return "data-resp(%s)" % str(self.value)


class PayloadArduinoResponse(GenericArduinoResponse):

  def __init__(self, typ, n):
    GenericArduinoResponse.__init__(self, ArduinoResponseType.PAYLOAD)
    self._array = None
    self._payload_type = typ
    self._n = n

  @property
  def payload_type(self):
    return self._payload_type

  @property
  def array(self):
    return self._array

  def set_array(self, data):
    assert (len(data) == self._n)
    self._array = data

  @staticmethod
  def parse(args):
    values = args[0].strip().split()
    typ = int(values[0])
    n = int(values[1])
    inbuf = values[2:]
    if not (len(values[2:]) == n):
      raise Exception("byte # mismatch: expected=%d, num=%d" % \
                      (int(n),len(values[2:])))

    resp = PayloadArduinoResponse(typ,n)
    buf = [0]*n
    for idx, val in enumerate(inbuf):
      buf[idx] = int(val)
    resp.set_array(buf)
    return resp

  def __repr__(self):
    return "payload-resp(%s,n=%d)" % (str(self._array), self._n)


def __arduino_command_header():
    return "AC:>"

def __parse_response(msg):
  rest = msg.strip().split(__arduino_command_header())[1]
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


def __is_response(msg):
  return msg.startswith(__arduino_command_header())


def get_response(ard,quiet=False):
  state = ArduinoResponseState.PENDING
  this_resp = None
  this_data = None
  data_idx = 0

  while True:
    line = ard.readline()
    if __is_response(line):
      resp = __parse_response(line)
      if resp.type == ArduinoResponseType.PROCESS:
        if not (state == ArduinoResponseState.PENDING):
          raise Exception("expected pending, received <%s>" % resp)
        state = ArduinoResponseState.PROCESSED

      elif resp.type == ArduinoResponseType.RESPONSE:
        assert (state == ArduinoResponseState.PROCESSED)
        state = ArduinoResponseState.WAITFOR_DATA
        this_resp = resp
        if this_resp.done():
          return this_resp

      elif resp.type == ArduinoResponseType.DATA:
        if resp.is_array():
          this_data = resp
          state = ArduinoResponseState.WAITFOR_PAYLOAD
        else:
          this_resp.set_data(data_idx, resp)
          data_idx += 1

        if this_resp.done():
          return this_resp

      elif resp.type == ArduinoResponseType.PAYLOAD:
        assert(state == ArduinoResponseState.WAITFOR_PAYLOAD)
        this_data.set_value(resp)
        this_resp.set_data(data_idx, this_data)
        data_idx += 1
        this_data = None
        state = ArduinoResponseState.WAITFOR_DATA

        if this_resp.done():
          return this_resp

      elif resp.type == ArduinoResponseType.MESSAGE:
        if not quiet:
          print("[msg] %s" % resp.message)
        if "ERROR:" in line:
          print("ERROR DETECTED..QUITTING...")
          ard.close()
          sys.exit(1)

      elif resp.type == ArduinoResponseType.DONE:
        if not quiet:
          print("<simulation finished>")
        continue

      elif resp.type == ArduinoResponseType.ERROR:
        raise Exception(resp.message)

      else:
        raise Exception("unhandled: %s" % line)
