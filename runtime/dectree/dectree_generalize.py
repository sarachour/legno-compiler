
import runtime.dectree.dectree as dectreelib

def add(dict_,par,val):
    if not par in dict_:
        dict_[par] = []
    dict_[par].append(val)

def dectree_generalize(physmodels):
    dectrees_by_par = {}
    uncertainties = {}
    for phys in physmodels:
        for name,dectree in phys.variables().items():
            add(dectrees_by_par,name,dectree)
            add(uncertainties,name,phys.uncertainty(name))

    for name,dectrees in dectrees_by_par.items():
        if all(map(lambda t: isinstance(t,dectreelib.RegressionLeafNode),dectrees)):
            variables = []
            uncs = uncertainties[name]
            for t in dectrees:
                variables += t.free_vars

            raise Exception("TODO: merge this")

        else:
            raise Exception("no strategy for merging decision trees.")
