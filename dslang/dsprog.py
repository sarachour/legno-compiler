import sys
from enum import Enum
import math
import numpy as np

import util.util as util

import ops.op as op
import ops.opparse as opparse
import ops.interval as intervallib
import os
import subprocess

def _evaluate(expr,vmap):
    vmap['math'] = math
    vmap['np'] = np
    vmap['randlist'] = util.randlist
    return np.real(eval(expr,vmap))

class DSProgDB:
    PROGRAMS = {}

    @staticmethod
    def register(name,dsprog,dssim,dsinfo):
        assert(not name in DSProgDB.PROGRAMS)
        DSProgDB.PROGRAMS[name] = (dsprog,dssim,dsinfo)

    @staticmethod
    def get_sim(name):
        DSProgDB.load()
        prog,sim,info = DSProgDB.PROGRAMS[name]
        return sim()

    @staticmethod
    def has_prog(name):
        DSProgDB.load()
        return name in DSProgDB.PROGRAMS

    @staticmethod
    def get_info(name):
        DSProgDB.load()
        prog,sim,info = DSProgDB.PROGRAMS[name]
        return info()

    @staticmethod
    def get_prog(name):
        DSProgDB.load()
        prog,sim,info = DSProgDB.PROGRAMS[name]
        prob = DSProg(name)
        prog(prob)
        prob.check()
        return prob

    @staticmethod
    def execute(name):
        prog,sim = DSProgDB.get(name)
        plot_diffeq(sim(), \
                    prog())

    @staticmethod
    def load():
        if len(DSProgDB.PROGRAMS) == 0:
            import progs

    def name(self):
        return NotImplementedError

class DSProg:
    class ExprType(Enum):
        INTEG = "integ"
        EXTERN = "extern"
        FN = "fn"

    def __init__(self,name):
        self._name = name
        self._bindings = {}
        self._lambdas = {}
        self._intervals = {}
        self._variables = []
        self._parameters = []

        self._time_constant_range = (None,None);
        self.max_time = 100.0

        self.__order = None
        self.__order_integs = None
        self.__types = None


    @property
    def parameters(self):
        return list(self._parameters)

    def speed(self,tmin,tmax):
        self._time_constant_range = (tmin,tmax)

    def time_constant(self):
        return self._time_constant_range

    def _compute_order(self):
        self.__order = []
        self.__order_integs = []
        self.__types = {}
        fns = []
        for var in self._variables:
            if not (var in self._bindings):
                continue

            if self._bindings[var].op == op.OpType.INTEG:
                self.__types[var] = DSProg.ExprType.INTEG
                self.__order.append(var)
                self.__order_integs.append(var)
            elif self._bindings[var].op == op.OpType.EXTVAR:
                self.__types[var] = DSProg.ExprType.EXTERN
                self.__order.append(var)

            else:
                self.__types[var] = DSProg.ExprType.FN
                fns.append(var)

        while not util.values_in_list(fns,self.__order):
            progress = False
            for var in fns:
                variables = self._bindings[var].vars()
                if util.values_in_list(variables,self.__order) and \
                   not var in self.__order:
                    self.__order.append(var)
                    progress = True

            print(fns)
            print(self.__order)
            assert(progress or util.values_in_list(fns,self.__order))


    def build_ode_prob(self):
        ics = {}
        fns = {}
        derivs = {}
        deriv_vars = []
        fn_vars = []
        for var in self.__order:
            typ = self.__types[var]
            if typ == DSProg.ExprType.INTEG:
                _,ics[var] = op.to_python(self._bindings[var].init_cond)
                _,derivs[var] = op.to_python(self._bindings[var].deriv)
                deriv_vars.append(var)
            else:
                _,fns[var] = op.to_python(self._bindings[var])
                fn_vars.append(var)
        return deriv_vars,ics,derivs, \
            fn_vars,fns


    def variables(self):
        return self._variables


    def _bind(self,var,expr):
        assert(not var in self._bindings)
        self._variables.append(var)
        self._bindings[var] = expr

    def decl_stvar(self,var,deriv,ic="0.0",params={}):
        deriv = opparse.parse(self,deriv.format(**params))
        ic = opparse.parse(self,ic.format(**params))
        expr = op.Integ(deriv,ic)
        self._bind(var,expr)

    def decl_var(self,var,expr,params={}):
        expr_conc = expr.format(**params)
        obj = opparse.parse(self,expr_conc)
        self._bind(var,obj)

    def decl_parameter(self,par):
        self._parameters.append(par)

    def decl_extvar(self,varname,loc):
        self._bind(varname,op.ExtVar("EXT_%s" % varname, \
                                     loc=loc))

    def emit(self,varexpr,obsvar,params={},loc='A0'):
        expr_conc = varexpr.format(**params)
        obj = opparse.parse(self,expr_conc)
        self._bind(obsvar,op.Emit(obj,loc='A0'))

    def lambda_spec(self,lambda_name):
        if not lambda_name in self._lambdas:
            raise Exception("lambda doesn't exist: <%s>" % lambda_name);

        variables,expr = self._lambdas[lambda_name]
        return variables,expr

    def lambda_specs(self):
        for name,(variables,expr) in self._lambdas.items():
            yield name,variables,expr

    def has_lambda(self,name):
        return name in self._lambdas

    def decl_lambda(self,lambda_name,expr,params={}):
        if lambda_name in self._lambdas:
            raise Exception("already exists: lambda <%s>" % lambda_name)

        expr_conc = opparse.parse(self,expr.format(**params))
        free_vars = set(expr_conc.vars())
        self._lambdas[lambda_name] = (free_vars,expr_conc)

    def bindings(self):
        for var,expr in self._bindings.items():
            yield var,expr

    def binding(self,v):
        if not v in self._bindings:
            return None
        return self._bindings[v]

    def get_interval(self,v):
        return self._intervals[v]

    def interval(self,v,min_v,max_v):
        assert(min_v <= max_v)
        assert(v in self._variables or v in self._parameters)
        self._intervals[v] = intervallib.Interval.type_infer(min_v,max_v)

    def intervals(self):
        for v,ival in self._intervals.items():
            yield v,ival


    def check(self):
        for variable,expr in self._bindings.items():
            if not (variable in self._intervals):
                if expr is None:
                    raise Exception("cannot infer ival: <%s> has no expression" \
                                    % variable)

                interval = intervallib.propagate_intervals(expr,self._intervals)
                self._intervals[variable] = interval


        if not (util.keys_in_dict(self._bindings.keys(), self._intervals)):
            for k in self._bindings.keys():
                if not k in self._intervals:
                    print("  :no ival %s" % k)
                else:
                    print("  :ival %s" % k)
            raise Exception("can't compile %s: missing intervals" % self.name)

        for p in self._parameters:
            if not p in self._intervals:
                raise Exception("can't compile hybrid program %s: missing intervals" % p)

        self._compute_order()

    @property
    def name(self):
        return self._name

    def __repr__(self):
        s = "prog %s\n" % self._name
        for p in self._parameteres:
            s += "par %s" % p
        for v,e in self._bindings.items():
            s += "  %s=%s\n" % (v,e)
        s += "\n"
        for v,i in self._intervals.items():
            s += "  iv %s=%s\n" % (v,i)


        return s

    def _execute(self,dssim):
        from scipy.integrate import ode
        stvars,ics,derivs,fnvars,fns = self.build_ode_prob()

        def dt_func(t,values):
            vs = dict(zip(map(lambda v: "%s" % v, stvars), \
                        values))
            for fvar in fnvars:
                vs["%s" % fvar] = _evaluate(fns[fvar],vs)

            next_vs = {}
            for stvar in stvars:
                next_vs[stvar] = _evaluate(derivs[stvar],vs)

            return list(map(lambda v: next_vs[v],stvars))

        time = dssim.sim_time
        n = 1000.0
        dt = time/n
        r = ode(dt_func).set_integrator('zvode',method='bdf')
        x0 = list(map(lambda v: _evaluate(ics[v],{}),stvars))
        r.set_initial_value(x0,t=0.0)
        T = []
        Y = []
        tqdm_segs = 500
        last_seg = 0
        while r.successful() and r.t < time:
            T.append(r.t)
            Y.append(r.y)
            r.integrate(r.t + dt)
            seg = int(tqdm_segs*float(r.t)/float(time))

        return T,Y


    def execute_and_profile(self, dssim):
        stvars,ics,derivs,fnvars,fns = self.build_ode_prob()
        stmts = []
        lhs_var = {}
        rhs_var = {}
        upd_var = {}
        order = []
        for idx,v in enumerate(stvars):
            upd_var["s%d" % idx] = "v[%d]" % idx
            lhs_var[v] = 'v[%d]' % idx;
            rhs_var["%s_" % v] = 's%d' % idx;
            order.append("%s_" % v)

        for idx,v in enumerate(fnvars):
            lhs_var[v] = 'v%d' % idx;
            rhs_var["%s_" % v] = 'v%d' % idx
            order.append("%s_" % v)

        order = sorted(order, key=lambda k: -len(k))
        def enq(stmt):
            stmts.append(stmt)

        for local,arr in upd_var.items():
            enq("%s=%s" % (local,arr))

        for var,expr in fns.items():
            for match in order:
                expr = expr.replace(match,rhs_var[match]);
            enq("%s=%s" % (lhs_var[var],expr))

        for var,expr in derivs.items():
            for match in order:
                expr = expr.replace(match,rhs_var[match]);
            enq("%s=%s" % (lhs_var[var],expr))

        enq("return v")

        func = ""
        func += "from numba import jit\n"
        func += "import sys\n"
        func += "import math\n"
        func += "import time\n"
        func += "import numpy as np\n"
        func += "from scipy.integrate import ode, odeint\n"
        func += "def func(v,t):\n"
        for st in stmts:
            func += "   %s\n" % st

        func += "t = np.linspace(0,%f,%d)\n"  \
                     % (dssim.sim_time,1000)
        func += "v = [0]*%d\n" % len(stvars)
        for var,prog_var in lhs_var.items():
            if var in stvars:
                func += "%s = %s;\n" % (prog_var,ics[var])
        func += "t1=time.time()\n"
        func += "R = odeint(func, v, t)\n";
        func += "t2=time.time()\n"
        func += "print(t2-t1)\n"
        with open('sim.py','w') as fh:
            fh.write(func)

        cmd = "python3 sim.py"
        result = subprocess.check_output(cmd, shell=True);
        return float(result)

    def execute(self,dssim):
        T,Y = self._execute(dssim)
        stvars,ics,derivs,fnvars,fns = self.build_ode_prob()
        def fn_func(t,values):
            vs = dict(zip(map(lambda v: v, stvars), \
                            values))
            vals = {}
            for fvar in fnvars:
                vals[fvar] = _evaluate(fns[fvar],vs)
                vs[fvar] = vals[fvar]

            for v in stvars:
                vals[v] = vs[v]
            return vals

        if(len(stvars) == 0):
            time = dssim.sim_time
            T = np.linspace(0,time,1000)
            Z =dict(map(lambda v: (v,[]), fnvars))
            for t in T:
                for var,value in fn_func(t,[]).items():
                    Z[var].append(value)

        else:
            Z =dict(map(lambda v: (v,[]), stvars+fnvars))
            for t,y in zip(T,Y):
                for var,value in fn_func(t,y).items():
                    Z[var].append(value)


        return T,Z
