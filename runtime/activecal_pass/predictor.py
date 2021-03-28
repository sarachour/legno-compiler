import runtime.runtime_util as runtime_util
import runtime.fit.model_fit as modelfitlib
import runtime.models.exp_phys_model as physlib

import runtime.activecal_pass.dominance as domlib

import hwlib.block as blocklib
import ops.base_op as baseoplib
import ops.generic_op as genoplib
import ops.lambda_op as lamboplib
import math


''''
This objective function encodes the block calibration objective. It maintains a
consistent ordering of output port multi-objective functions.
'''
class MultiOutputObjective:

    def __init__(self):
        self._objectives = {}
        self._outputs = []
        self._errors = {}


    @property
    def outputs(self):
        return self._outputs

    def objective(self,out):
        return self._objectives[out]

    def add_error(self,out,err):
        if not out.name in self._errors:
            self._errors[out.name] = []

        self._errors[out.name].append(err)

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


    def make_result(self,values):
        result = domlib.Result()
        index = 0
        for out,name,obj,tol,prio in self:
           result.add(name,values[index],tol,prio)
           index += 1

        assert(index == len(values))
        return result


    def make_distance_expr(self,objs):
        vals = [0.0]*len(self)
        res = self.make_result(vals)
        return res.distance_expr(objs)


    def compute(self,delta_params,errors):
        values = []
        var_dict = dict(delta_params)
        for out,name,obj,tol,prio in self:
            model_error = 0.0
            for idx,value in errors[out].items():
                assert(isinstance(value,float))
                model_error += abs(value)

            model_error /= len(errors[out].keys())
            var_dict[out][blocklib.MultiObjective.MODEL_ERROR] = model_error
            values.append(obj.compute(var_dict[out]))

        return self.make_result(values)

    def __iter__(self):
        for out in self._outputs:
            multi_obj = self.objective(out)
            for obj,tol,prio  in multi_obj:
               name = str(obj)
               yield out,name,obj,tol,prio

    def __len__(self):
        cnt = 0
        for _ in self:
            cnt += 1
        return cnt

'''
A subclass for managing the data the predictor parameters are
elicited from
'''
class Data:

    def __init__(self,block,output,variable):
        self.output = output
        self.hidden_codes = list(map(lambda hc: hc.name,  \
                                     runtime_util.get_hidden_codes(block)))
        self.codes = []
        self.values = []
        self.clear()


    def clear(self):
        self.codes = []
        self.values = []

    def add_datapoint(self,codes,val):
        hcs = []
        for code in self.hidden_codes:
            hcs.append(codes[code])

        self.values.append(val)
        self.codes.append(hcs)

    def get_dataset(self):
        codes = dict(map(lambda hc : (hc,[]), self.hidden_codes))
        for hcs in self.codes:
            for hc_name,value in zip(self.hidden_codes, hcs):
                codes[hc_name].append(value)
        return codes,list(self.values)

class ErrorData(Data):

    def __init__(self,block,output,index):
        self.output = output
        self.index = index
        Data.__init__(self,block,output,blocklib.MultiObjective.MODEL_ERROR)


class VariablePredictionModel:

    def __init__(self,block,output,variable,expr):
        assert(isinstance(expr,physlib.Param))
        assert(isinstance(block,blocklib.Block))
        assert(isinstance(output,blocklib.BlockOutput))

        self.block = block
        self.output = output
        self.variable = variable
        self.model= expr
        self.model_error = 0.0
        self.values = {}
        self.conc_expr = None
        self._concretized = False

    @staticmethod
    def get_key(out,var):
        output = out if isinstance(out,str) else out.name
        return "%s.%s" % (output,var)

    @property
    def key(self):
        return VariablePredictionModel.get_key(self.output,self.variable)

    @property
    def concrete(self):
        return self._concretized

    def clear(self):
        self.conc_expr = None
        self._concretized = False
        self.values = {}
        self.model_error = 0.0

    def min_samples(self):
        return len(self.model.params) + 1

    def fit(self,codes,values):
        npts = len(values)
        if len(values) == 0:
            raise Exception("no data for fitting variable <%s> at output <%s>" % (var,out))

        try:
            result = modelfitlib.fit_model(self.model.params,self.model.expr,{'inputs':codes,'meas_mean':values})
        except Exception as e:
            print("[WARN] failed to predict <%s> for output <%s> of block <%s>" % (self.key, \
                                                                                   self.output.name, \
                                                                                   self.block.name))
            print("   %s.%s var=%s expr=%s" % (self.block.name,self.output.name,self.key,self.model.expr))
            print("   EXCEPTION=%s" % e)
            return

        for par in self.model.params:
            self.values[par] = result['params'][par]

        subst = dict(map(lambda tup: (tup[0],genoplib.Const(tup[1])), \
                            self.values.items()))
        self.conc_expr = self.model.expr.substitute(subst)
        self._concretized = True

        error = 0.0
        all_errors = []
        for idx in range(npts):
            assigns = dict(map(lambda hc: (hc,codes[hc][idx]), codes.keys()))
            pred = self.conc_expr.compute(assigns)
            all_errors.append(values[idx]-pred)
            error += (values[idx]-pred)**2

        self.model_error = math.sqrt(error)/npts
        print("%s.%s npts=%d deltavar=%s error=%s expr=%s" \
                    % (self.block.name,self.output.name, \
                       npts, self.key, self.model_error, self.conc_expr))
        for idx,(v,e) in enumerate(zip(values,all_errors)):
            ci = dict(map(lambda c: (c,codes[c][idx]), codes.keys()))
            #print("   codes=%s value=%s error=%s" % (ci,v,e))

    def predict(self,hidden_codes):
        value = self.conc_expr.compute(hidden_codes)
        return value
 
class ErrorPredictionModel(VariablePredictionModel):

    def __init__(self,block,output,index,expr):
        self.index = index
        VariablePredictionModel.__init__(self,block,output,blocklib.MultiObjective.MODEL_ERROR,expr)

    @staticmethod
    def get_prefix(out):
        output = out if isinstance(out,str) else out.name
        prefix = "%s.%s" % (output,blocklib.MultiObjective.MODEL_ERROR)
        return prefix

    @staticmethod
    def get_key(out,var):
        output = out if isinstance(out,str) else out.name
        return "%s.%s(%s)" % (output,blocklib.MultiObjective.MODEL_ERROR,var)

    @property
    def key(self):
        return ErrorPredictionModel.get_key(self.output,self.index)


class Predictor:
    '''
    The full symbolic predictor. This predictor is able to take a set of hidden codes
    and predict each of the sub-objective functions. We can then use the dominance test to choose the best one
    '''
    def __init__(self,blk,loc,cfg):
        self.variables = {}
        self.error_models = {}
        self.data = {}

        self.block = blk
        self.loc = loc
        self.config= cfg

    def predict(self,hidden_codes):
        variables = {}
        model_errors = {}
        for out in self.block.outputs:
            variables[out.name] = {}
            model_errors[out.name] = {}

        for var_model in self.variables.values():
            assert(var_model.concrete)
            value = var_model.predict(hidden_codes)
            variables[var_model.output.name][var_model.variable] = value

        for err_model in self.error_models.values():
            assert(err_model.concrete)
            value = err_model.predict(hidden_codes)
            model_errors[err_model.output.name][err_model.index] = value

        return variables, model_errors

    def substitute(self,output,expr):
        assert(isinstance(expr, baseoplib.Op))
        vdict = {}
        for var_model in self.variables.values():
            assert(var_model.concrete)
            vdict[var_model.variable] = var_model.conc_expr

        terms = []
        prefix = ErrorPredictionModel.get_prefix(output)
        for key in self.error_models.keys():
            if prefix in key:
                terms.append(lamboplib.Abs(self.error_models[key].conc_expr))

        model_error_expr = genoplib.Mult(genoplib.Const(1.0/len(terms)), \
                            genoplib.sum(terms))
        vdict[blocklib.MultiObjective.MODEL_ERROR] = model_error_expr
        return expr.substitute(vdict)


    def add_variable_datapoint(self,output,var,hcs,val):
        assert(isinstance(val,float))
        key = VariablePredictionModel.get_key(output,var)
        if not key in self.variables:
            raise Exception("no variable with key <%s>" % key)

        self.data[key].add_datapoint(hcs,val)

    def add_error_datapoint(self,output,index,hcs,val):
        assert(isinstance(val,float))
        key = ErrorPredictionModel.get_key(output,index)
        if not key in self.error_models:
            raise Exception("no variable with key <%s>" % key)

        self.data[key].add_datapoint(hcs,val)


    def set_model_error(self,out,mdl):
        assert(isinstance(mdl,physlib.ExpPhysErrorModel))
        for index,point in mdl.points(self.block):
            vpred = ErrorPredictionModel(self.block,out,index,point)
            if vpred.key in self.error_models:
                raise Exception("already in model error predictor <%s>" % vpred.key)

            self.error_models[vpred.key] = vpred
            self.data[vpred.key] = ErrorData(self.block,out,index)

    def set_variable(self,out,v,mdl):
        assert(isinstance(mdl,physlib.Param))
        if mdl is None:
            raise Exception("no physical model for <%s> of output <%s>" % (v,out.name))

        vpred = VariablePredictionModel(self.block,out,v,mdl)
        if vpred.key in self.variables:
            raise Exception("variable already modeled <%s>" % vpred.key)

        self.variables[vpred.key] = vpred
        self.data[vpred.key] = Data(self.block,out,v)

    def clear(self):
        for model in self.variables.values():
            model.clear()

        for model in self.error_models.values():
            model.clear()

    def min_samples(self):
        return max(map(lambda v: v.min_samples(), self.variables.values()))


    def fit(self):
        for key,model in self.error_models.items():
            codes,values = self.data[key].get_dataset()
            model.fit(codes,values)

        for key,model in self.variables.items():
            codes,values = self.data[key].get_dataset()
            model.fit(codes,values)

        if any(map(lambda v: not v.concrete, self.variables.values())) or \
           any(map(lambda v: not v.concrete, self.error_models.values())):
               raise Exception("could not infer parametres for <%s> in output <%s>" % (var,out))
