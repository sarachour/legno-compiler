import math
import numpy as np
import ops.op as oplib

def select_from_array(arr,n):
  space = math.ceil(len(arr)/n)
  subarr = arr[0:len(arr):space]
  return subarr

def select_from_interval(ival,n):
  return list(np.linspace(ival.lower,ival.upper,n))

def select_from_quantized_interval(ival,quant,n):
  values = quant.get_values(ival)
  return select_from_array(values,n)

def is_integration_op(expr):
  if expr.op == oplib.OpType.INTEG:
    return True
  else:
    return any(map(lambda arg: is_integration_op(arg), \
                   expr.args))

def get_subarray(arr,inds):
  return list(map(lambda i: arr[i], inds))
