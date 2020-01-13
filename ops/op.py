import numpy as np
import random

from ops.generic_op import *
from ops.lambda_op import *

def mkadd(terms):
    if len(terms) == 0:
        return Const(0)
    elif len(terms) == 1:
        return terms[0]
    elif len(terms) == 2:
        return Add(terms[0],terms[1])
    else:
        curr = Add(terms[0],terms[1])
        for i in range(2,len(terms)):
            curr = Add(curr,terms[i])
        return curr
