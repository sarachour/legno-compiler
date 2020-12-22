import hwlib.adp as adplib
import runtime.dectree.dectree as dectreelib
import runtime.runtime_util as runtime_util
import runtime.models.database as dblib
import ops.generic_op as genoplib

import numpy as np
import math

# models joint distrubtion of uncertainties
class UncertaintyModel:

    def __init__(self):
        self.errors = {}
        self.metadata = {}
        self.variables = []

    @property
    def mean(self):
      mean = np.array(list(map(lambda v: np.mean(self.errors[v]), \
                               self.variables)))
      return mean


    @property
    def covariance(self):
      n_samps = min(map(lambda err: len(err), self.errors.values()))
      data = list(map(lambda v: self.errors[v][:n_samps], self.variables))
      covariance = np.cov(np.array(data),bias=True)
      return covariance

    def _key(self,out,v):
      return "%s.%s" % (out.name,v)

    def set_error(self,out,v,pred,obs):
      key = self._key(out,v)
      assert(not key in self.variables)
      n = min(len(pred),len(obs))
      self.errors[key] = list(map(lambda i: (pred[i]-obs[i]), \
                                range(n)))
      self.variables.append(key)
      self.metadata[key] = (out.name,v)

    def summarize(self):
        cov = self.covariance
        mean = self.mean
        print("==== Uncertainty Summary ====")
        #for v,errs in self.errors.items():
        #    print("---- VAR %s ----" % (v))
        #    print(errs)

        #print("")
        #print('------------')
        for idx,var in enumerate(self.variables):
            print("var %s mu=%f std=%f" \
                  % (var, mean[idx], math.sqrt(cov[idx][idx])))

        print("")
        for i1,v1 in enumerate(self.variables):
            for i2,v2 in enumerate(self.variables):
                if i1 >= i2:
                    continue

                print("vars (%s,%s) cov=%e" \
                      % (v1,v2, cov[i1][i2]))

        print("===========================")

    def samples(self,count,ampl=1.0,include_zero=False):
      n_vars = len(self.variables)
      cov = self.covariance
      mean = self.mean
      samps = np.random.multivariate_normal(mean=mean.reshape(n_vars,), \
                                            cov=cov, \
                                            size=count)
      if include_zero:
        yield dict(zip(self.variables, \
                       [0.0]*n_vars))
      for samp in samps:
        yield dict(zip(self.variables, \
                       map(lambda v: ampl*float(v), samp)))

    def verify_covariance(self):
        n_vars = len(self.variables)
        dataset = list(map(lambda v: [], range(n_vars)))
        for samp in self.samples(100):
          for idx,val in enumerate(samp):
                dataset[idx].append(val)

        cov = np.cov(dataset,bias=True)
        return cov

    @staticmethod
    def from_json(obj):
      mdl = UncertaintyModel()
      mdl.errors = obj['errors']
      mdl.variables = obj['variables']
      mdl.metadata = obj['metadata']
      return mdl

    def to_json(self):
      return {
        'errors':self.errors,
        'variables':self.variables,
        'metadata':self.metadata
      }





class ExpPhysModel:
  MODEL_ERROR = "modelError"

  def __init__(self,blk,cfg):
    self.block = blk
    self.config = cfg
    self._params = {}
    self._model_errors = {}
    self._uncertainty = UncertaintyModel()

  def _key(self,out,var):
    return "%s.%s" % (out.name,var)

  def calib_obj(self):
    glb_objs = []
    for out in self.block.outputs:
        obj = out.deltas[self.config.mode].objective
        variables = dict(map(lambda v: (v,genoplib.Var(self._key(out,v))),  \
                             set(obj.vars())))
        glb_obj = obj.copy().substitute(variables)
        glb_objs.append(glb_obj)

    calib_obj = genoplib.sum(glb_objs)
    return calib_obj


  @property
  def uncertainty(self):
    return self._uncertainty

  @property
  def model_errors(self):
    return dict(self._model_errors.items())


  @property
  def params(self):
    return dict(self._params.items())

  def variables(self):
    variables = dict(list(self.params.items()) + \
                     list(self.model_errors.items()))
    return variables

  def model_error(self,out):
      key = self._key(out,ExpPhysModel.MODEL_ERROR)
      return self._model_errors[key]

  def set_variable(self,out,name,tree):
    if name == ExpPhysModel.MODEL_ERROR:
      self.set_model_error(out,tree)

    else:
      self.set_param(out,name,tree)

  def set_model_error(self,out,tree):
      key = self._key(out,ExpPhysModel.MODEL_ERROR)
      assert(isinstance(tree,dectreelib.Node))
      self._model_errors[key] = tree

  def set_param(self,out,par,tree):
      key = self._key(out,par)
      assert(isinstance(tree,dectreelib.Node))
      self._params[key] = tree

  def random_sample(self):
    samples = []
    for par,dectree in self.params.items():
      samples += dectree.random_sample(samples)

    samples += self.model_error.random_sample(samples)

    return samples

  @property
  def static_cfg(self):
    return runtime_util\
      .get_static_cfg(self.block,self.config)



  def hidden_codes(self):
    for st in filter(lambda st: isinstance(st.impl,blocklib.BCCalibImpl), \
                     self.block.state):
      yield st.name,self.config[st.name].value

  def to_json(self):
    param_dict = {}
    for par,model in self._params.items():
      param_dict[par] = model.to_json()

    modelerr_dict = {}
    for err,model in self._model_errors.items():
      modelerr_dict[err] = model.to_json()

    return {
      'block': self.block.name,
      'config': self.config.to_json(),
      'params': param_dict,
      'model_errors':modelerr_dict,
      'uncertainties':self._uncertainty.to_json(),
    }
  #'phys_model': self.phys_models.to_json(),


  def __repr__(self):
    st = "%s\n" % self.config
    for par,dectree in self._params.items():
      unc = self.uncertainty(par)
      st += "===== %s (unc=%f) =====\n" % (par,unc)
      st += str(dectree.pretty_print())

    return st



  def copy_from(self,other):
    assert(self.block.name == other.block.name)
    assert(self.static_cfg == other.static_cfg)
    self.config = other.cfg.copy()
    self._params = {}
    for par,tree in other._params.items():
      self._params[par] = tree.copy()
    self._model_error = other.model_error.copy()
    self._uncertainties = dict(other._uncertainties)

  @staticmethod
  def from_json(dev,obj):
    blk = dev.get_block(obj['block'])
    cfg = adplib.BlockConfig.from_json(dev,obj['config'])
    assert(not blk is None)
    mdl = ExpPhysModel(blk,cfg)
    for par,subobj in obj['params'].items():
      mdl._params[par] = dectreelib.Node.from_json(subobj)

    for merr,subobj in obj['model_errors'].items():
      mdl._model_errors[merr] = dectreelib.Node.from_json(subobj)

    mdl._uncertainty = UncertaintyModel.from_json(obj['uncertainties'])
    return mdl


def __to_phys_models(dev,matches):
  for match in matches:
    yield ExpPhysModel.from_json(dev, \
                                 runtime_util.decode_dict(match['model']))

def load(dev,blk,cfg):
    where_clause = {
      'block': blk.name,
      'static_config': runtime_util.get_static_cfg(blk,cfg)
    }
    matches = list(dev.physdb.select(dblib \
                                  .PhysicalDatabase \
                                  .DB.PHYS_MODELS,
                                  where_clause))
    if len(matches) == 1:
      return list(__to_phys_models(dev,matches))[0]

    elif len(matches) == 0:
      pass
    else:
      raise Exception("can only have one match")

def update(dev,model):
    assert(isinstance(model,ExpPhysModel))
    where_clause = {
      'block': model.block.name,
      'static_config': model.static_cfg
    }
    insert_clause = dict(where_clause)
    insert_clause['model'] = runtime_util \
                             .encode_dict(model.to_json())

    matches = list(dev.physdb.select(dblib\
                                     .PhysicalDatabase \
                                     .DB.PHYS_MODELS,where_clause))
    if len(matches) == 0:
      dev.physdb.insert(dblib \
                        .PhysicalDatabase \
                        .DB.PHYS_MODELS,insert_clause)
    elif len(matches) == 1:
      dev.physdb.update(dblib \
                        .PhysicalDatabase \
                        .DB.PHYS_MODELS, \
                        where_clause, insert_clause)


