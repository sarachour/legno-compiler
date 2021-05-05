import numpy as np

class Tabular():

    def __init__(self,fields,fmt):
        self.sorting_field = None
        self.fields = fields
        self.fmt = fmt
        self.rows = []
        self.emphasis = []

    def sort_by(self,field):
        assert(field in self.fields)
        self.sorting_field = field

    def add(self,values,emph=None):
        assert(len(values) == len(self.fields))
        self.rows.append(values)
        self.emphasis.append(emph)

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
            fields = []
            for j,cell in enumerate(self.rows[i]):
                value =  self.fmt[j] % cell if not cell is None else ""
                if not self.emphasis[i] is None and self.emphasis[i][j]:
                    value = "\\textbf{%s}" % value
                fields.append(value)


            st += " & ".join(fields)
            st += "\\\\\n"
        return st

