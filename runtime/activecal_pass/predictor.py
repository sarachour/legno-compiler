import runtime.runtime_util as runtime_util
import runtime.fit.model_fit as modelfitlib

import runtime.activecal_pass.dominance as domlib

import hwlib.block as blocklib
import ops.generic_op as genoplib
import math


''''
This objective function encodes the block calibration objective. It maintains a
consistent ordering of output port multi-objective functions.
'''
class MultiOutputObjective:

    def __init__(self):
        self._objectives = {}
        self._outputs = []

    @property
    def outputs(self):
        return self._outputs

    def objective(self,out):
        return self._objectives[out]


    @property
    def priorities(self):
        ps = []
        for obj in self._objectives.values():
            ps += obj.priorities
        return list(set(ps))

    def add(self,out,obj):
        if not (isinstance(obj, blocklib.MultiObjective)):
           raise Exception("for out <%s>: not a multiobjective argument: %s" % (out.name,obj))

        self._outputs.append(out.name)
        self._objectives[out.name] = obj


    def compute(self,delta_params):
        values = []
        for out in self.outputs:
            multi_obj = self.objective(out)
            for obj in multi_obj.objectives:
                val = obj.compute(delta_params[out])
                values.append(val)

        return domlib.Result.make(self,values)

    def __iter__(self):
        for out in self._outputs:
            for obj in self._objectives[out].objectives:
                yield out,obj


'''
A subclass for managing the data the predictor parameters are
elicited from
'''
class Data:

    def __init__(self,outputs,hidden_codes):
        self.outputs = outputs
        self.hidden_codes = list(map(lambda hc: hc.name, hidden_codes))
        self.variables = []
        self.dataset = {}
        self.clear()


    def clear(self):
        for out in self.outputs:
            variables = list(self.dataset[out].keys()) if out in self.dataset else []
            self.dataset[out] = {}
            for var in variables:
                self.dataset[out][var] = {'codes':[],'values':[]}

    def add_variable(self,output,var):
        self.dataset[output.name][var] = {'codes':[], 'values':[]}

    def add_datapoint(self,output,var,codes,val):
        hcs = []
        for code in self.hidden_codes:
            hcs.append(codes[code])

        self.dataset[output.name][var]['values'].append(val)
        self.dataset[output.name][var]['codes'].append(hcs)

    def get_dataset(self,output,var):
        ds = self.dataset[output.name][var]
        values = ds['values']
        codes = dict(map(lambda hc : (hc,[]), self.hidden_codes))
        for hcs in ds['codes']:
            for hc_name,value in zip(self.hidden_codes, hcs):
                codes[hc_name].append(value)
        return codes,values

class Predictor:

    '''
    The full symbolic predictor. This predictor is able to take a set of hidden codes
    and predict each of the sub-objective functions. We can then use the dominance test to choose the best one
    '''
    def __init__(self,blk,loc,cfg):
        self.variables = {}
        self.concrete_variables = {}
        self.block = blk
        self.loc = loc
        self.config= cfg
        self.data = Data(list(map(lambda o: o.name, self.block.outputs)), \
                                   runtime_util.get_hidden_codes(self.block))
        self.values = {}
        self.errors = {}

    def predict(self,hidden_codes):
        delta_params = {}
        delta_errors = {}
        for (out,var),expr in self.concrete_variables.items():
            value = expr.compute(hidden_codes)
            # write predicted value to delta parameter dictionary
            if not out in delta_params:
                delta_params[out] = {}
                delta_errors[out] = {}
            delta_params[out][var] = value
            delta_errors[out][var] = self.errors[(out,var)]

        return delta_params,delta_errors

    def set_variable(self,out,v,mdl):
        assert(not (out.name,v) in self.variables)
        if mdl is None:
            raise Exception("no physical model for <%s> of output <%s>" % (v,out.name))
        self.variables[(out.name,v)] = mdl
        self.data.add_variable(out,v)

    def clear(self):
        self.data.clear()
        self.conc_variables = {}

    def min_samples(self):
        return max(map(lambda v: len(v.params) + 1, self.variables.values()))


    def fit(self):
        for (out,var),model in self.variables.items():
            codes,values = self.data.get_dataset(self.block.outputs[out],var)
            npts = len(values)
            if len(values) == 0:
                raise Exception("no data for fitting variable <%s> at output <%s>" % (var,out))

            try:
               result = modelfitlib.fit_model(model.params,model.expr,{'inputs':codes,'meas_mean':values})
            except Exception as e:
               print("[WARN] failed to predict <%s> for output <%s> of block <%s>" % (var,out,self.block.name))
               print("   %s.%s deltavar=%s expr=%s" % (self.block.name,out,var, model.expr))
               print("   EXCEPTION=%s" % e)
               continue

            self.values[(out,var)] = {}
            for par in model.params:
                self.values[(out,var)][par] = result['params'][par]

            subst = dict(map(lambda tup: (tup[0],genoplib.Const(tup[1])), \
                             self.values[(out,var)].items()))
            conc_expr = model.expr.substitute(subst)
            self.concrete_variables[(out,var)] = conc_expr

            error = 0.0
            all_errors = []
            for idx in range(npts):
               pred = conc_expr.compute(dict(map(lambda hc: (hc,codes[hc][idx]), self.data.hidden_codes)))
               all_errors.append(values[idx]-pred)
               error += (values[idx]-pred)**2

            self.errors[(out,var)] = math.sqrt(error)/npts
            print("%s.%s npts=%d deltavar=%s error=%s expr=%s" \
                       % (self.block.name,out,npts, var,self.errors[(out,var)], conc_expr))
            for idx,(v,e) in enumerate(zip(values,all_errors)):
                ci = dict(map(lambda c: (c,codes[c][idx]), codes.keys()))
                #print("   codes=%s value=%s error=%s" % (ci,v,e))

        for (out,var),model in self.variables.items():
            if not (out,var) in self.concrete_variables:
               raise Exception("could not infer parametres for <%s> in output <%s>" % (var,out))
