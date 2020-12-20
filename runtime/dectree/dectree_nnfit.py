from keras.models import Sequential
from keras.layers import Dense, Dropout,Input
import math
import numpy as np
from scipy import optimize
import ops.generic_op as genoplib
import runtime.dectree.dectree as dectreelib

class NeuralNetwork:

    def __init__(self,n_inputs):
        self.model = Sequential()
        self.model.add(Input(shape=(n_inputs,)))
        n_reps = 3
        factor = 2**(n_reps+1)
        for reps in range(n_reps):
            self.model.add(Dense(n_inputs*factor, \
                                activation='relu', \
                                kernel_initializer="uniform"))
            if n_reps < 2:
                self.model.add(Dropout(0.4))
            factor /= 2


        self.model.add(Dense(1, \
                             use_bias=True,
                             activation='linear'))

        self.model.compile(loss='mean_squared_error',  \
                           optimizer='adam')


    def fit(self,x,y,epochs=150, batch_size=10):
        self.model.fit(x,y,epochs=150,batch_size=10,verbose=0)


    def predict(self,x):
        return self.model.predict(x)



    def evaluate(self,x,y):
        acc = self.model.evaluate(x,y)
        return acc


class SymbolicFunction:
    class Parameter:
        def __init__(self,value):
            self.value = value

        def set(self,value):
            self.value = value

        def __call__(self):
            return self.value

    def __init__(self,n_inputs):
        self.dim = n_inputs

    def initialize(self,x,y,npts=14):
        dataset = []
        for idx in range(self.dim):
            datum = list(map(lambda xs: xs[idx], x))
            dataset.append(datum)

        corrs = np.cov(dataset,y)

        coords = []
        scores = []
        for i in range(self.dim):
            for j in range(self.dim):
                scores.append(-abs(corrs[i][j]))
                coords.append((i,j))

        indices = np.argsort(scores)
        for i in range(npts):
            idx = indices[i]
            i,j = coords[idx]
            print("i=%d j=%d score=%f" % (i,j,scores[idx]))

        self.num_params = npts + 1
        self.parameters = list(map(lambda _: SymbolicFunction.Parameter(1.0), \
                                   range(self.num_params)))

        self.coords = coords[:npts]



    def _func(self,x):
        result = self.parameters[0]()
        offset = 1
        for i,j in self.coords:
            p = self.parameters[offset]
            if i == j:
                result += p()*x[i]
            else:
                result += p()*x[i]*x[j]
            offset += 1


        return result

    def _symbolic_model(self,names):
        param = lambda p : "p%d" % p
        assert(len(names) == self.dim)
        terms = []
        assigns = {}
        terms.append(genoplib.Var(param(0)))
        offset = 1

        for i,j in self.coords:
            v1 = names[i]
            v2 = names[j]
            if i == j:
                t = genoplib.Mult(genoplib.Var(param(offset)), \
                              genoplib.Var(v1))
            else:
                t = genoplib.Mult(genoplib.Var(param(offset)), \
                              genoplib.Mult( \
                                             genoplib.Var(v1), \
                                             genoplib.Var(v2)))

            terms.append(t)
            assigns[param(offset)] = self.parameters[offset]()
            offset += 1

        expr = genoplib.sum(terms)
        return expr,assigns

    def _weight(self,yi,ys):
        absval = max(np.abs(ys))
        err = 1.0 - abs(yi/absval)
        return err

    def fit(self,x,y):
        npts = len(y)
        def func(pars):
            for i,p in enumerate(self.parameters):
                p.set(pars[i])

            return list(map(lambda i: (y[i] - self._func(x[i]))*self._weight(y[i],y), \
                            range(npts)))

        params = [param() for param in self.parameters]
        result =optimize.leastsq(func,params, \
                                 full_output=True)
        pars,cov,info,mesg,ier = result
        for i,p in enumerate(self.parameters):
            p.set(pars[i])


    def predict(self,x):
        npts = len(x)
        return list(map(lambda i: self._func(x[i]), \
                        range(npts)))


    def extract_decision_tree(self):
        model = self._symbolic_model()




def fit_poly_decision_tree(hidden_code_fields, codes, values, npars):
    n_codes = len(hidden_code_fields)
    n_samps = len(codes)
    model = SymbolicFunction(n_codes)
    model.initialize(codes,values,npars)
    model.fit(codes,values)

    predict = model.predict(codes)


    print('----')
    for v,p in zip(values,predict):
        pcterr = (v-p)/v*100.0 
        print("   %f pred=%f wt=%0.2f err=%0.2f %%"  \
              % (v,p,model._weight(v,values), pcterr))


    expr,assigns = model._symbolic_model(hidden_code_fields)
    node = dectreelib.RegressionLeafNode(expr,npts=n_samps,params=assigns)
    return node,predict

def fit_nn_decision_tree(hidden_code_fields, codes, values, bounds, max_depth, min_size):
    n_codes = len(hidden_code_fields)
    n_samps = len(codes)
    nn = NeuralNetwork(n_codes)
    absval = np.mean(np.abs(values)) 
    dataset = []
    for _ in range(n_samps):
        dataset.append([0]*n_codes)

    for i,cs in enumerate(codes):
        for j,c in enumerate(cs):
            dataset[i][j] = float(c)

    nn.fit(list(dataset),values,epochs=1000,batch_size=n_samps)
    predict = nn.predict(dataset)
    for v,p in zip(values,predict):
        print("   %f pred=%f" % (v,p))

    mse = nn.evaluate(dataset,values)
    print("MSE %.4e" % (mse))
    print("Ampl: %.5f" % absval)
    fracerr = math.sqrt(mse)/absval
    print("Pct Err: %.2f" % (100*fracerr))
    input()

def fit_decision_tree(hidden_code_fields, codes, values, npars):
    return fit_poly_decision_tree(hidden_code_fields, codes, values, npars)
