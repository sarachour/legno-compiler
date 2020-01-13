from enum import Enum
from lab_bench.lib import cstructs,enums

class BoolType(str,Enum):
    TRUE = 'true'
    FALSE = 'false'

    def boolean(self):
        if self == BoolType.TRUE:
            return True
        else:
            return False

    @staticmethod
    def from_bool(b):
        if b:
            return BoolType.TRUE
        else:
            return BoolType.FALSE

    @staticmethod
    def from_code(code):
        if code == 0:
            return BoolType.FALSE
        else:
            return BoolType.TRUE

    def code(self):
        if BoolType.TRUE == self:
            return 1
        else:
            return 0

class PortType(str,Enum):
    IN0 = "in0"
    IN1 = "in1"
    OUT0 = "out0"
    OUT1 = "out1"
    OUT2 = "out2"

    def to_code(self):
        codes = {
            PortType.IN0: 0,
            PortType.IN1: 1,
            PortType.OUT0: 2,
            PortType.OUT1: 3,
            PortType.OUT2: 4
        }
        return codes[self]

    @staticmethod
    def from_code(i):
        codes = {
            0: PortType.IN0,
            1: PortType.IN1,
            2: PortType.OUT0,
            3: PortType.OUT1,
            4: PortType.OUT2
        }
        return codes[i]

class SignType(str,Enum):
    POS = 'pos'
    NEG = 'neg'

    @staticmethod
    def option_names():
        for opt in SignType.options():
            yield opt.name


    @staticmethod
    def has(v):
      assert(isinstance(v,Enum))
      for name in SignType.option_names():
        if v.name == name:
          return True
      return False


    @staticmethod
    def options():
        yield SignType.POS
        yield SignType.NEG

    @staticmethod
    def from_abbrev(msg):
        if msg == "+":
            return SignType.POS
        elif msg == "-":
            return SignType.NEG
        else:
            raise Exception("unknown")


    def coeff(self):
        if SignType.POS == self:
            return 1.0
        elif SignType.NEG == self:
            return -1.0
        else:
            raise Exception("unknown")

    def abbrev(self):
        if self == SignType.POS:
            return '+'
        elif self == SignType.NEG:
            return '-'
        else:
            raise Exception("unknown")

    def code(self):
        if self == SignType.POS:
            return False
        elif self == SignType.NEG:
            return True

    def __repr__(self):
        return self.abbrev()


class CircLoc:

    def __init__(self,chip,tile,slice,index=None):
        self.chip = chip;
        self.tile = tile;
        self.slice = slice;
        self.index = index;

    @staticmethod
    def from_json(obj):
        return CircLoc(
            chip=obj['chip'],
            tile=obj['tile'],
            slice=obj['slice'],
            index=obj['index']
        )

    def to_json(self):
        return {
            'chip': self.chip,
            'tile': self.tile,
            'slice': self.slice,
            'index': self.index
        }

    def __hash__(self):
        return hash(str(self))

    def __eq__(self,other):
        if isinstance(other,CircLoc):
            return self.chip == other.chip \
                and self.tile == other.tile \
                and self.slice == other.slice \
                and self.index == other.index
        else:
            return False


    def build_ctype(self):
        if self.index is None:
            return {
                'chip':self.chip,
                'tile':self.tile,
                'slice':self.slice
            }
        else:
            return {
                'loc':{
                    'chip':self.chip,
                    'tile':self.tile,
                    'slice':self.slice
                },
                'idx':self.index
            }

    def __repr__(self):
        if self.index is None:
            return "loc(ch=%d,tile=%d.slice=%d)" % \
                (self.chip,self.tile,self.slice)
        else:
            return "loc(ch=%d,tile=%d,slice=%d,idx=%d)" % \
                (self.chip,self.tile,self.slice,self.index)

class CircPortLoc:

    def __init__(self,chip,tile,slice,port,index=None):
        self.loc = CircLoc(chip,tile,slice,index)
        assert(isinstance(port,int) or port is None)
        self.port = port

    def to_json(self):
        return {
            'loc': self.loc.to_json(),
            'port_id': self.port
        }

    def build_ctype(self):
        if self.loc.index is None:
            loc = CircLoc(self.loc.chip,
                          self.loc.tile,
                          self.loc.slice,
                          0)
        else:
            loc = self.loc

        port = self.port if not self.port is None else 0
        return {
            'idxloc':loc.build_ctype(),
            'idx2':port
        }

    def __hash__(self):
        return hash(str(self))


    def __eq__(self,other):
        if isinstance(other,CircPortLoc):
            return self.loc == other.loc and self.port == other.port
        else:
            return False

    def __repr__(self):
        return "port(%s,%s)" % (self.loc,self.port)

