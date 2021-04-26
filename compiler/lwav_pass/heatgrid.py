import numpy as np
import matplotlib.pyplot as plt

class NormalizedHeatGrid:

    def __init__(self,name,title,xlabel,resolution,bounds=(0,1)):
        self.name = name
        self.title = title
        self.resolution = resolution
        self.xlabel = xlabel
        self.series = []
        self.bounds = bounds

    def add_row(self,data):
        self.series.append(data)


    def plot(self,filename):
        borders = list(np.linspace(0.0,1.0,self.resolution))[:-1]
        data = []
        for values in self.series:
            buckets = [0]*len(borders)
            for val in values:
                best_bord = max(filter(lambda bord: val >= bord, borders))
                index = borders.index(best_bord)
                buckets[index] += 1

            total = sum(buckets)
            for idx,value in enumerate(buckets):
                buckets[idx] = float(value)/total

            data.append(buckets)

        l,u = self.bounds
        tick_labels = list(map(lambda b: "%.2f" % ((u-l)*b+l), borders))

        fig,ax = plt.subplots()
        ax.imshow(np.array(data))
        ax.set_title(self.name)
        ax.set_xlabel(self.xlabel)
        ax.set_xticklabels(tick_labels)
        ax.set_yticklabels("")
        fig.tight_layout()
        plt.savefig(filename)
