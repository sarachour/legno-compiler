import numpy as np
import os
import hwlib.props as props
import hwlib.units as units
import hwlib.hcdc.globals as glb
import hwlib.hcdc.enums as enums
import ops.interval as interval
import util.util as gutil
import math

truncate = gutil.truncate
equals = gutil.equals

def datapath(filename):
    return "hwlib/hcdc/data/%s" % filename

def build_coeff_cstr(cstrlst,expr):
    contcstrlst = []

    slack = 0.0
    for var,coeff in cstrlst:
        if coeff == 1.0:
            val = interval.Interval.type_infer(1.0,1.0)
        elif coeff ==10.0:
            val = interval.Interval.type_infer(10.0,10.0)
        elif coeff == 0.1:
            val = interval.Interval.type_infer(0.1,0.1)
        else:
            val = interval.Interval.type_infer(0.0,0.0)
        contcstrlst.append((var,(expr,val)))
    return contcstrlst


def build_oprange_cstr(cstrlst,scale):
    contcstrlst = []
    slack = 1.2

    for var,rng in cstrlst:
        if rng == hwlibcmd.RangeType.MED:
            cstr = 1.0
        elif rng == hwlibcmd.RangeType.LOW:
            cstr = 0.1
        elif rng == hwlibcmd.RangeType.HIGH:
            cstr = 10.0

        contcstrlst.append((var,cstr))
    return contcstrlst

def make_ana_props(rng,ival):
    lb,ub = ival
    assert(lb < ub)
    prop = props.AnalogProperties() \
                .set_interval(lb*rng.coeff(),
                              ub*rng.coeff(),
                              unit=units.uA)
    return prop

def make_dig_props(rng,ival,npts):
    lb,ub = ival
    start = lb*rng.coeff()
    end = ub*rng.coeff()
    hcdcv2_values = np.linspace(start,end,npts)
    info = props.DigitalProperties() \
                .set_values(hcdcv2_values)
    error = np.mean(np.diff(hcdcv2_values))
    return info

def apply_blacklist(options,blacklist):
    def in_blacklist(opt,blist):
        for entry in blacklist:
            match = True
            for ov,ev in zip(opt,entry):
                if not ev is None and ov != ev:
                    match = False
            if match:
                return True

        return False

    for opt in options:
        if in_blacklist(opt,blacklist):
            continue
        yield opt
