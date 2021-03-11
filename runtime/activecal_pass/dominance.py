from enum import Enum

class Result:

    def __init__(self):
        self.values = []
        self.tolerances = []
        self.priorities = []
        self.by_priority = {}

    def add(self,value,tol,prio):
        n = len(self.values)
        self.values.append(value)
        self.tolerances.append(tol)
        self.priorities.append(prio)

    def compatible(self,other):
        if len(self.values) != len(self.values):
            return False

        for p1,p2,t1,t2 in zip(self.priorities,other.priorities, \
                               self.tolerances,other.tolerances):
            if p1 != p2 or abs(t1-t2) > 1e-5:
                return False

        return True


    @staticmethod
    def make(multiobj,values):
        objs = Result()
        idx = 0
        for out in multiobj.outputs:
            subobj = multiobj.objective(out)
            for obj,tol,prio in subobj:
                objs.add(values[idx],tol,prio)
                idx += 1
        assert(idx == len(values))
        return objs

    def distance(self):
        scores = []
        max_prio = max(self.priorities)
        for value,tol,prio in zip(self.values,self.tolerances,self.priorities):
            subscore = (10**(max_prio-prio))*value/tol
            scores.append(subscore)
        
        score = sum(scores)
        return score

    # to make things sortable
    def __lt__(self,other):
        assert(self.compatible(other))
        return self.distance() < other.distance()

    def __iter__(self):
        for v in self.values:
            yield v


    def __repr__(self):
        valstr = " ".join(map(lambda v: "%.2e" % v, self.values))
        return "score=%s values=[%s]" % (self.distance(), valstr)

class Relationship:
   class Type(Enum):
       DOM = "dom"
       EQUAL = "equal"
       SUB = "sub"

   def __init__(self,kind,rank):
        self.kind = kind
        self.rank = rank

   def __repr__(self):
        return "%s(%d)" % (self.kind.value,self.rank)

def multi_dominant(self,v1,v2):
    idx = 0
    results = []
    for out in self._outputs:
        n = len(self._objectives[out].objectives)
        vs1 = v1[idx:idx+n]
        vs2 = v2[idx:idx+n]
        results.append(self._objectives[out].dominant(vs1,vs2))
        idx += n

    subs =  list(filter(lambda res: blocklib.Relationship.Type.SUB == res.kind, results))
    doms =  list(filter(lambda res: blocklib.Relationship.Type.DOM== res.kind, results))

    if len(subs) > 0:
        idx = np.argmax(map(lambda s: -s.rank, subs))
        return blocklib.Relationship(blocklib.Relationship.Type.SUB, subs[idx].rank)

    if len(doms) > 0:
        idx = np.argmax(map(lambda s: -s.rank, doms))
        return blocklib.Relationship(blocklib.Relationship.Type.DOM, doms[idx].rank)

    return blocklib.Relationship(blocklib.Relationship.Type.EQUAL, 1)

def dominant(self,vs1,vs2,strict=False):
    results = []
    for prio in self.priorities:
        better = False
        worse = False
        num_better = 0
        num_worse = 0
        num_equal = 0
        for idx in self.by_priority[prio]:
            eps = self.epsilons[idx] if not strict else 0.0

            if vs1[idx]-eps > vs2[idx]+eps:
                if self.minimize:
                    num_worse +=1
                else:
                    num_better += 1

            if vs1[idx]+eps < vs2[idx]-eps:
                if self.minimize:
                    num_better += 1
                else:
                    num_worse += 1

            if abs(vs1[idx] - vs2[idx]) <= eps:
                num_equal += 1

        if num_better > 0 and num_worse == 0:
            results.append(Relationship.Type.DOM)
        elif num_worse > 0:
            results.append(Relationship.Type.SUB)
        else:
            results.append(Relationship.Type.EQUAL)

    if any(map(lambda r: r == Relationship.Type.SUB, results)):
        for idx,result in enumerate(results):
            if result == Relationship.Type.SUB:
                return Relationship(Relationship.Type.SUB,idx+1)

    for idx,result in enumerate(results):
        if result == Relationship.Type.DOM:
            return Relationship(Relationship.Type.DOM,idx+1)

    return Relationship(Relationship.Type.EQUAL,1)

def to_score(obj,scores):
    assert(isinstance(obj,predlib.MultiObjective))
    raise Exception("ffff")

