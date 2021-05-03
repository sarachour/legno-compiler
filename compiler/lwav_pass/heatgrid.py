import numpy as np
import matplotlib.pyplot as plt
class HeatGrid:

    def __init__(self,name,title,xlabel,ylabel,resolution):
        self.name = name
        self.title = title
        self.resolution = resolution
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.series = []
        self.bounds = None

        self.numerical_rows = False
        self.row_values = []
        self.show_xlabel = True
        self.show_ylabel = True
        self.show_xticks = True
        self.show_yticks = True

    def add_row(self,data,value=None):
        self.series.append(data)
        if self.bounds is None:
            self.bounds = [min(data),max(data)]

        self.bounds[0] = min(min(data),self.bounds[0])
        self.bounds[1] = max(max(data),self.bounds[1])
        if self.numerical_rows:
            assert(not value is None)
            self.row_values.append(value)


    def render_subplot(self,ax,bounds=None):
        bounds = self.bounds if bounds is None else bounds
        borders = list(np.linspace(bounds[0], \
                                   bounds[1], \
                                   self.resolution))[:-1]
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

        ax.imshow(np.array(data))
        ax.set_title(self.name,fontsize=10)
        if self.show_xlabel:
            ax.set_xlabel(self.xlabel,fontsize=12)

        if not self.show_xticks:
            ax.get_xaxis().set_visible(False)


        if self.show_ylabel:
            ax.set_ylabel(self.ylabel,fontsize=12)

        if not self.show_yticks:
            ax.get_yaxis().set_visible(False)

        ax.set_xticks([0,self.resolution-1])
        ax.set_xticklabels([ \
                             "%.2f" % borders[0],  \
                             "%.2f" % borders[-1]], \
                           fontsize=10)


        if not self.numerical_rows:
            ax.set_yticklabels("")
        else:
            ticks = ax.get_yticks()
            labels = list(map(lambda t: "%.2f" % self.row_values[int(t)] \
                              if t >= 0 and t <= len(self.row_values) else "", ticks))
            ax.set_yticklabels(labels,fontsize=10)

    def plot(self,filename):
        fig,ax = plt.subplots()
        self.render_subplot(ax)
        fig.tight_layout()
        plt.savefig(filename)

class MultiHeatGrid:

    def __init__(self,name,xlabel,ylabel):
        self.name = name
        self.heatgrids = []
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.bounds = None

    def add(self,plt):
        self.heatgrids.append(plt)
        if self.bounds is None:
                self.bounds = list(plt.bounds)

        self.bounds[0] = min(self.bounds[0], plt.bounds[0])
        self.bounds[1] = max(self.bounds[1], plt.bounds[1])

    def plot(self,filename):
        fig,axs = plt.subplots(1,len(self.heatgrids))
        for idx,(ax,hg) in enumerate(zip(axs,self.heatgrids)):
            hg.show_xlabel = False
            hg.show_xticks = False
            if idx != 0:
                hg.show_ylabel = False
                hg.show_yticks = False
                hg.numerical_rows = False
            hg.render_subplot(ax,bounds=self.bounds)


        fig.tight_layout()
        plt.savefig(filename)

