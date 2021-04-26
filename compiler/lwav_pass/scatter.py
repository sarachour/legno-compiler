from enum import Enum

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


class ScatterVis:

    def __init__(self,name,title,xlabel,ylabel):
        self.name = name
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title
        self.points = {}
        self.styles = {}
 
    @property
    def time_units(self):
        for wf in self.waveforms.values():
            return wf.time_units
        return None

    @property
    def num_series(self):
        return len(self.points.keys())

    @property
    def empty(self):
        return self.num_series== 0

    def add_series(self,name,xs,ys):
        assert(len(xs) == len(ys))
        self.points[name] = (xs,ys)


    def set_style(self,name,color,pointstyle,opacity=1.0):
        self.styles[name] = (color,pointstyle,opacity)


    def plot(self,filepath):
        palette = sns.color_palette()
        ax = plt.subplot(1, 1, 1)
        title = self.title
        ax.tick_params(labelsize=24);
        ax.set_xlabel(self.xlabel,fontsize=28)
        ax.set_ylabel(self.ylabel,fontsize=28)
        ax.set_title(title,fontsize=32)
        ax.grid(False)

        for name,(xs,ys) in self.points.items():
            color,pointstyle,opacity = self.styles[name]
            ax.scatter(xs,ys,label=name,
                       marker=pointstyle, \
                       s=100,\
                       color=color, \
                       alpha=opacity)

        #ax.set_ylim(ymin=ymin*1.1,ymax=ymax*1.1)
        #ax.set_xlim(xmin=xmin*1.1,xmax=xmax*1.1)

        plt.tight_layout()
        plt.savefig(filepath)
        plt.clf()

