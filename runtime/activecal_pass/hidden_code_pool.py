import runtime.runtime_util as runtime_util

import runtime.activecal_pass.predictor as predlib
import runtime.activecal_pass.dominance as domlib

import numpy as np
import math

class ParetoPoolView:

    def __init__(self,objectives,name):
        assert(isinstance(objectives, predlib.MultiOutputObjective))
        self.name = name
        self.multi_objective = objectives
        self.values = []

    def add(self,v):
        assert(isinstance(v, domlib.Result) or v is None)
        self.values.append(v)

    def get_best(self,debug=False):
        for idx,score in self.order_by_dominance(debug):
            return idx,score

    def order_by_dominance(self,debug=False):
        dists = list(map(lambda v: v.distance(), self.values))
        indices = list(np.argsort(dists))
        for i in indices:
            yield i,self.values[i]



''''
The pool of hidden codes to sample from when performing calibration.
The pool maintains a set of hidden codes and a symbolic predictor which guesses
the function value from the set of hidden code values

'''
class HiddenCodePool:

    def __init__(self,variables,predictor,objectives):
        self.variables = variables
        self.predictor = predictor
        self.objectives = objectives
        self.ranges = {}
        self.pool = []
        self.pool_keys = []

        self.meas_view = ParetoPoolView(self.objectives,'meas')
        self.pred_view = ParetoPoolView(self.objectives,'pred')

    def set_range(self,var,values):
        self.ranges[var] = values

    def get_values(self,v):
        return self.ranges[v]

    def default_sample(self):
        codes = {}
        for c in self.variables:
            mid = math.floor(len(self.ranges[c])/2)
            codes[c] = self.ranges[c][mid]

        return codes

    def random_sample(self):
        codes = {}
        for c in self.variables:
            codes[c] = random.choice(self.ranges[c])

        return codes

    def has_code(self,codes):
        key = runtime_util.dict_to_identifier(codes)
        return key in self.pool_keys

    def get_unlabeled(self):
        for idx,(mv,p) in enumerate(zip(self.meas_view.values,self.pool)):
            if mv is None:
                yield self.pred_view.values[idx],dict(zip(self.variables,p))

    def has_code(self,codes):
        key = runtime_util.dict_to_identifier(codes)
        return key in self.pool_keys

    def add_unlabeled_code(self,codes):
        key = runtime_util.dict_to_identifier(codes)
        if key in self.pool_keys:
            raise Exception("code already in pool: %s" % (codes))

        self.pool_keys.append(key)

        pred_deltavars,pred_model_errors  = self.predictor.predict(codes)
        pred_obj = self.objectives.compute(pred_deltavars,pred_model_errors)
        vals = list(map(lambda v: codes[v], self.variables))
        self.pool.append(vals)
        self.meas_view.add(None)
        self.pred_view.add(pred_obj)


    def update_predicted_label(self,codes):
        key = runtime_util.dict_to_identifier(codes)
        if not key in self.pool_keys:
            raise Exception("cannot update code <%s> which doesn't belong to pool.")

        idx = self.pool_keys.index(key)
        pred_deltavars,pred_model_errors  = self.predictor.predict(codes)
        pred_obj = self.objectives.compute(pred_deltavars,pred_model_errors)
        self.pred_view.values[idx] = pred_obj 


    def update_predicted_labels(self):
        for code_values in self.pool:
            self.update_predicted_label(dict(zip(self.variables,code_values)))

    def affix_label_to_code(self,codes,variables,errors):
        key = runtime_util.dict_to_identifier(codes)
        assert(key in self.pool_keys)
        idx = self.pool_keys.index(key)
        if not self.meas_view.values[idx] is None:
            print(self.meas_view.values[idx])
            raise Exception("there is already a label for this code <%s>" % (str(codes)))

        meas = self.objectives.compute(variables,errors)
        self.meas_view.values[idx] = meas
        return meas


    def add_labeled_code(self,codes,actual_delta_vars,actual_model_errors):
        key = runtime_util.dict_to_identifier(codes)
        if key in self.pool_keys:
            raise Exception("code already tested: %s score=%f" % (codes,score))

        self.pool_keys.append(key)

        meas_obj = self.objectives.compute(actual_delta_vars,actual_model_errors)
        pred_delta_vars,pred_model_errors = self.predictor.predict(codes)
        pred_obj = self.objectives.compute(pred_delta_vars,pred_model_errors)

        vals = list(map(lambda v: codes[v], self.variables))
        self.pool.append(vals)
        self.meas_view.add(meas_obj)
        self.pred_view.add(pred_obj)

    @property
    def ranking(self):
        for idx,key in enumerate(self.keys):
           yield self.scores[idx]
 
    def num_codes(self):
        return len(self.keys)
