import numpy as np

class Tabular():

    def __init__(self,fields,fmt):
        self.sorting_field = None
        self.fields = fields
        self.fmt = fmt
        self.rows = []

    def sort_by(self,field):
        assert(field in self.fields)
        self.sorting_field = field

    def add(self,values):
        assert(len(values) == len(self.fields))
        self.rows.append(values)

    def render(self):
        st = " & ".join(map(lambda f: str(f), self.fields))
        st += "\\\\\n"
        indices = list(range(len(self.rows)))
        if not self.sorting_field is None:
            idx = self.fields.index(self.sorting_field)
            sort_values = list(map(lambda row: row[idx], self.rows))
            indices = np.argsort(sort_values)
        else:
            indices = list(range(len(self.rows)))

        for i in indices:
            st += " & ".join(map(lambda f: f[0] % f[1] if not f[1] is None else "", \
                                zip(self.fmt,self.rows[i])))
            st += "\\\\\n"
        return st

