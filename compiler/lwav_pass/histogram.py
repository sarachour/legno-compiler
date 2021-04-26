from enum import Enum

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np



class HistogramVis:

    def __init__(self,name,xaxis,title,bins):
        self.name = name
        self.title = title
        self.xlabel = xaxis
        self.bounds = None
        self.bins = max(1,int(bins))
        self.data= {}
        self.styles = {}
 
    @property
    def time_units(self):
        for wf in self.waveforms.values():
            return wf.time_units
        return None

    def set_bounds(self,minval,maxval):
        self.bounds = (minval,maxval)

    @property
    def num_series(self):
        return len(self.data.keys())

    @property
    def empty(self):
        return self.num_waveforms == 0

    def add_data(self,name,datum):
        self.data[name] = datum


    def set_style(self,name,color,opacity=1.0):
        self.styles[name] = (color,opacity)


    def plot(self,filepath):
        palette = sns.color_palette()
        ax = plt.subplot(1, 1, 1)
        title = self.title
        ax.tick_params(labelsize=24);
        ax.set_xlabel(self.xlabel,fontsize=28)
        ax.set_title(title,fontsize=32)

        ax.grid(False)

        ymax = ymin = 0.0
        for name,dat  in self.data.items():
            print(name)
            if name in self.styles:
                color,opacity = self.styles[name]
                ax.hist(dat,bins=self.bins,
                        color=color, \
                        alpha=opacity, \
                        label=name)
            else:
                ax.hist(dat,bins=self.bins,
                        label=name)


        if not self.bounds is None:
            ax.set_xlim(xmin=self.bounds[0], \
                        xmax=self.bounds[1])

        if len(self.data.keys()) > 0:
            ax.legend()

        plt.tight_layout()
        plt.savefig(filepath)
        plt.clf()

