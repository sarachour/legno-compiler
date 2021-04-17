import cProfile
import json
import zlib
import numpy as np
import binascii
import time
import util.config as CONFIG
import os
from enum import Enum
import parse as parselib


def array_map(mapfun):
    return np.array(list(mapfun))


class CalibrateObjective(Enum):
    MIN_ERROR = "min_error"
    MAX_FIT = "max_fit"
    FAST = "fast"

class DeltaModel(Enum):
    DELTA_MINERR = "delta-min_error"
    DELTA_MAXFIT = "delta-max_fit"
    NAIVE_MINERR = "naive-min_error"
    NAIVE_MAXFIT = "naive-max_fit"
    IDEAL = "ideal"

    def abbrev(self):
        if DeltaModel.DELTA_MINERR == self:
            return "de"
        if DeltaModel.DELTA_MAXFIT == self:
            return "dg"
        elif DeltaModel.NAIVE_MINERR == self:
            return "ne"
        elif DeltaModel.NAIVE_MAXFIT == self:
            return "ng"
        elif DeltaModel.IDEAL == self:
            return "i"

    @staticmethod
    def from_abbrev(x):
      if x == "de":
        return DeltaModel.DELTA_MINERR
      elif x == "dg":
        return DeltaModel.DELTA_MAXFIT
      elif x == "ne":
        return DeltaModel.NAIVE_MINERR
      elif x == "ng":
        return DeltaModel.NAIVE_MAXFIT
      elif x == "i":
        return DeltaModel.IDEAL
      else:
        raise Exception("unknown abbrev")

    def uses_uncertainty(self):
        return False

    def naive_model(self):
        if self == DeltaModel.DELTA_MINERR:
            return DeltaModel.NAIVE_MINERR
        elif self == DeltaModel.DELTA_MAXFIT:
            return DeltaModel.NAIVE_MAXFIT

    def uses_delta_model(self):
        if self == DeltaModel.DELTA_MINERR or \
           self == DeltaModel.DELTA_MAXFIT:
            return True
        else:
            return False

    def calibrate_objective(self):
        if self == DeltaModel.DELTA_MAXFIT or \
           self == DeltaModel.NAIVE_MAXFIT:
            return CalibrateObjective.MAX_FIT
        else:
            return CalibrateObjective.MIN_ERROR

def model_format():
    cmd = [
        "{model:w}d{pct_mdpe:f}a{pct_mape:f}v{pct_vmape:.2f}c{pct_mc:f}", \
        "{model:w}d{pct_mdpe:f}a{pct_mape:f}v{pct_vmape:.2f}c{pct_mc:f}b{bandwidth_khz:f}k" \
    ]
    return cmd

# pack model from model_format function
def pack_parsed_model(args):
    model = DeltaModel.from_abbrev(args['model'])
    mdpe = args['pct_mdpe']/100.0
    mape = args['pct_mape']/100.0
    mc = args['pct_mc']/100.0
    vmape = args['pct_vmape']/100.0
    bandwidth_hz = None
    if 'bandwidth_khz' in args:
        bandwidth_hz = args['bandwidth_khz']*1000.0

    return pack_model(model,mdpe,mape,vmape,mc,bandwidth_hz)

def pack_model(model,mdpe,mape,vmape,mc,bandwidth_hz=None):
    model_enum = DeltaModel(model)
    args = {
        'model': model_enum.abbrev(),
        'pct_mdpe': mdpe*100.0,
        'pct_mape': mape*100.0,
        'pct_vmape': vmape*100.0,
        'pct_mc': mc*100.0
    }
    if bandwidth_hz is None:
        cmd = "{model}d{pct_mdpe:.2f}a{pct_mape:.2f}v{pct_vmape:.2f}c{pct_mc:.2f}"
    else:
        args['bandwidth_khz'] = bandwidth_hz/1000.0
        cmd = "{model}d{pct_mdpe:.2f}a{pct_mape:.2f}v{pct_vmape:.2f}c{pct_mc:.2f}b{bandwidth_khz:.2f}k"

    return cmd.format(**args)


def unpack_model(name):
    for subcmd in model_format():
        result = parselib.parse(subcmd,name)
        if not result is None:
            args = dict(result.named.items())
            return {
                "model":DeltaModel.from_abbrev(args['model']),
                'pct_mdpe':args['pct_mdpe'],
                'pct_mape':args['pct_mape'],
                'pct_vmape':args['pct_vmape'],
                'pct_mc':args['pct_mc'],
                "mdpe": args['pct_mdpe']/100.0,
                "mape": args['pct_mape']/100.0,
                "vmape": args['pct_vmape']/100.0,
                "mc": args['pct_mc']/100.0,
                'bandwidth_khz': args['bandwidth_khz'] \
                if 'bandwidth_khz' in args else None,
                'bandwidth_hz': args['bandwidth_khz']*1000.0 \
                if 'bandwidth_khz' in args else None
            }

def randlist(seed,n):
  np.random.seed(seed)
  return list(map(lambda _ : np.random.uniform(-1,1),range(n)))


def mkdir_if_dne(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

class Timer:

    def __init__(self,name,ph):
        self._runs = []
        self._name = name
        self._paths = ph

    def runs(self):
        return list(self._runs)

    def start(self):
        self._start = time.time()

    def kill(self):
        self._start = None

    def end(self):
        end = time.time()
        self._runs.append(end-self._start)
        self._start = None

    def __repr__(self):
        if len(self._runs) == 0:
            return "%s mean=n/a std=n/a"

        mean = np.mean(self._runs)
        std = np.std(self._runs)
        return "%s mean=%s std=%s" % (self._name,mean,std)

    def save(self):
        filename = self._paths.time_file(self._name)
        with open(filename,'w') as fh:
            fh.write("%s\n" % self._name)
            for run in self._runs:
                fh.write("%f\n" % run)

    def __repr__(self):
        if len(self._runs) == 0:
            return "%s npts=0" % (self._name)
        else:
            mean = np.mean(self._runs)
            std = np.std(self._runs)
            return "%s npts=%d mean=%s std=%s" % (self._name,len(self._runs),mean,std)


    @staticmethod
    def load(name,ph):
        filename = ph.time_file(name)
        timer = Timer(name,ph)
        if not os.path.exists(filename):
            return timer

        with open(filename,'r') as fh:
            fh.readline()
            for line in fh:
                timer._runs.append(float(line))

        return timer


def flatten(dictionary, level = []):
    tmp_dict = {}
    for key, val in dictionary.items():
        if type(val) == dict:
            tmp_dict.update(flatten(val, level + [key]))
        else:
            tmp_dict['.'.join(level + [key])] = val
    return tmp_dict

def unflatten(dictionary):
    resultDict = dict()
    for key, value in dictionary.items():
        parts = key.split(".")
        d = resultDict
        for part in parts[:-1]:
            if part not in d:
                d[part] = dict()
            d = d[part]
        d[parts[-1]] = value
    return resultDict


def partition(boolfn,lst):
    yes = []
    no = []
    for el in lst:
        if boolfn(el):
            yes.append(el)
        else:
            no.append(el)
    return yes,no

def values_in_list(vals,lst):
  for val in vals:
    if not val in lst:
      return False
  return True

def keys_in_dict(keys,dict_):
  for key in keys:
    if not key in dict_:
      return False
  return True

def pos_inf(f):
  return f == float('inf')

def equals(f1,f2):
  return abs(f1-f2) <= 1e-5

def nearest_value(values,value,index=False):
    scores = list(map(lambda v: abs(value-v),\
                      values))
    idx = np.argmin(scores)
    if index:
        return idx
    else:
        return values[idx]

def decompress_json(hexstr):
  byte_obj = binascii.unhexlify(hexstr)
  comp_obj = zlib.decompress(byte_obj)
  obj = json.loads(str(comp_obj,'utf-8'))
  return obj

def compress_json(obj):
  byte_obj=json.dumps(obj).encode('utf-8')
  comp_obj = zlib.compress(byte_obj,3)
  strdata = str(binascii.hexlify(comp_obj), 'utf-8')
  return strdata

def truncate(f, n):
  '''Truncates/pads a float f to n decimal places without rounding'''
  s = '{}'.format(f)
  if 'e' in s or 'E' in s:
    return '{0:.{1}f}'.format(f, n)
  i, p, d = s.partition('.')
  return float('.'.join([i, (d+'0'*n)[:n]]))

def profile(fn):
  cp = cProfile.Profile()
  cp.enable()
  fn()
  cp.disable()
  cp.print_stats()
  input("continue.")

def is_inf(v):
  return v == float('inf')

def normalize_mode(m):
    if isinstance(m,list):
        m = tuple(m)

    if isinstance(m,tuple):
        return tuple(map(lambda mi: normalize_mode(mi), m))

    elif isinstance(m,Enum):
        return m.value
    else:
        return str(m)

def get_subarray(arr,inds):
  return list(map(lambda i: arr[i], inds))


def remove_nans(arr):
  nparr = np.array(arr)
  return nparr[:,~np.isnan(nparr).any(axis=0)]

def singleton(en):
    items = list(en)
    if len(items) == 0:
        raise Exception("singleton: cannot cast empty array to singleton")

    elif len(items) > 1:
        raise Exception("singleton: cannot cast array wit >1 els (%s) to singleton" % items)

    return items[0]

 
