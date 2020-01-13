import compiler.lscale_pass.objective.basic_obj as boptlib

#TODO: what is low range, high range and med range?
#TODO: setRange: integ.in, integ.out and mult have setRange functions.
#TODO: how do you set wc in the integrator? Is it through the setRange function?
class LScaleObjectiveFunctionManager():

    @staticmethod
    def basic_methods():
        return [
            #boptlib.FastObjFunc,
            #boptlib.StateVarObjFunc,
            boptlib.FastObsObjFunc,
            #boptlib.SlowObsObjFunc
        ]

    def __init__(self,scenv):
        self.method = None
        self.scenv = scenv
        self._results = {}


    @property
    def time_scaling(self):
        return self.scenv.time_scaling

    def result(self,objective):
        return self._results[objective]

    def add_result(self,objective,sln):
        self._results[objective] = sln


    def objective(self,circuit):
        assert(not self.method is None)
        gen = None
        for obj in self.basic_methods():
            if obj.name() == self.method:
                gen = obj.make(circuit,self)

        for obj in gen:
            yield obj
