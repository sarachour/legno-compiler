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

    def transpose(self):
        header = [self.fields[0]] + list(map(lambda r: r[0], self.rows))
        tbl = Tabular(header, ["%s"]*len(header))
        for col_id in range(1,len(self.fields)):
            new_row = [self.fields[col_id]]
            for row in self.rows:
                cell = row[col_id]
                value =  self.fmt[col_id] % cell if not cell is None else ""
                new_row.append(value)

            tbl.add(new_row)

        return tbl

    def render(self):
        st = " & ".join(map(lambda f: str(f), self.fields))
        st += "\\\\\n"
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

