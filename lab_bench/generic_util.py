from enum import Enum
import numpy as np
import math as math
import util.util as util

class RoundMode(Enum):
    UP = "up"
    DOWN = "down"
    NEAREST = "nearest"

# number of bytes. number of padding..
def compute_pad_bytes(n,x):
    if x < n:
        raise Exception("cannot compute padding: padded=%d data=%d" % (x,n))

    over = n % x
    left = x - over
    return left

def code_to_val(code):
    assert(code < 256)
    assert(code >= 0)
    return (code - 128.0)/128.0

def find_closest(array,value,round_mode):
    sel_value = None
    if round_mode == RoundMode.NEAREST:
        dist,sel_value = min(map(lambda cv: (abs(cv-value),cv), array), \
                             key=lambda pair:pair[0])


    elif round_mode == RoundMode.UP:
        s_array = sorted(array)
        for curr_val in array:
            if curr_val >= value and sel_value is None:
                sel_value = curr_val

        if sel_value is None:
            sel_value = array[-1]

        dist = abs(value-sel_value)

    elif round_mode == RoundMode.DOWN:
        s_array = sorted(array,reverse=True)
        for curr_val in array:
            if curr_val >= value and sel_value is None:
                sel_value = curr_val
        if sel_value is None:
            sel_value = array[-1]

        dist = abs(value-sel_value)

    return dist,sel_value

def uniform(master,index):
    st = np.random.get_state()
    seed = hash("%d.%d" % (master,index)) & 0xffffffff
    np.random.seed(seed)
    value = np.random.uniform()
    np.random.set_state(st)
    return value

def eval_func(fn,args):
    args['math'] = math
    args['np'] = np
    args['randlist'] = util.randlist
    args['random_uniform'] = uniform
    return eval(fn,args)
